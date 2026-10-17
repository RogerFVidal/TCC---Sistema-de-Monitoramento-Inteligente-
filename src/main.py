
import cv2
import math
import time

from pathlib import Path
from collections import deque
from dataclasses import dataclass, field

from ultralytics import YOLO
from logs import registrar_log as registrar_log_arquivo


# ==================== CONFIGURAÇÕES ====================

CONFIANCA_DETECCAO = 0.55
CONFIANCA_KEYPOINT = 0.45

ANGULO_SUSPEITO = 60.0
ANGULO_ERETO = 30.0

TAMANHO_BUFFER = 15
PROPORCAO_SUSPEITA = 0.80
FRAMES_RECUPERACAO = 10
TEMPO_EXPIRACAO_TRACK = 3.0

AREA_MINIMA_CAIXA = 5000
ALTURA_MINIMA_CAIXA = 80
PROPORCAO_MINIMA_CAIXA = 0.20
PROPORCAO_MAXIMA_CAIXA = 1.50


def localizar_modelo():
    """Localiza os pesos do YOLO na pasta src ou na raiz."""
    pasta_atual = Path(__file__).resolve().parent

    candidatos = [
        pasta_atual / "yolov8n-pose.pt",
        pasta_atual.parent / "yolov8n-pose.pt",
        Path.cwd() / "yolov8n-pose.pt",
    ]

    for caminho in candidatos:
        if caminho.is_file():
            return str(caminho)

    # O Ultralytics tentará localizar ou baixar o modelo.
    return "yolov8n-pose.pt"


@dataclass
class EstadoPessoa:
    """Histórico individual de cada pessoa rastreada."""

    posturas_suspeitas: deque = field(
        default_factory=lambda: deque(maxlen=TAMANHO_BUFFER)
    )
    historico_ereto: deque = field(
        default_factory=lambda: deque(maxlen=45)
    )

    centro_y_referencia: float = None
    ultimo_visto: float = 0.0
    alerta_enviado: bool = False
    frames_recuperacao: int = 0


class DetectorQuedas:
    def __init__(self, callback_log=None):
        self.callback_log = callback_log
        self.is_running = False
        self.estados = {}

    def parar(self):
        """Solicita que o monitoramento pare."""
        self.is_running = False

    def parada_solicitada(self, verificar_parada=None):
        """Verifica os dois mecanismos de parada disponíveis."""
        if not self.is_running:
            return True

        if verificar_parada is not None:
            try:
                return bool(verificar_parada())
            except Exception as erro:
                self.log(
                    f"[ERRO] Falha ao verificar parada: {erro}"
                )
                return True

        return False

    def log(self, mensagem):
        """Grava a mensagem e a encaminha para a interface."""
        try:
            registrar_log_arquivo(mensagem)
        except Exception as erro:
            print(f"[ERRO] Não foi possível gravar o log: {erro}")

        if self.callback_log:
            try:
                self.callback_log(mensagem)
            except Exception as erro:
                print(f"[ERRO] Não foi possível atualizar o painel: {erro}")
        else:
            print(mensagem)

    @staticmethod
    def caixa_eh_valida(x1, y1, x2, y2):
        """Ignora caixas pequenas ou com proporções improváveis."""
        largura = max(0, x2 - x1)
        altura = max(0, y2 - y1)

        if largura == 0 or altura == 0:
            return False

        area = largura * altura
        proporcao = largura / altura

        if altura < ALTURA_MINIMA_CAIXA:
            return False

        if area < AREA_MINIMA_CAIXA:
            return False

        if not (
            PROPORCAO_MINIMA_CAIXA
            <= proporcao
            <= PROPORCAO_MAXIMA_CAIXA
        ):
            return False

        return True

    @staticmethod
    def calcular_inclinacao(keypoints):
        """
        Calcula o desvio do tronco em relação à vertical.
        Retorna (ângulo, centro dos ombros, centro dos quadris).
        """
        indices = [5, 6, 11, 12]

        if len(keypoints) <= max(indices):
            return None, None, None

        pontos = keypoints[indices]

        # Ignora pontos corporais com confiança insuficiente.
        if pontos.shape[1] >= 3:
            for confianca in pontos[:, 2]:
                if (
                    not math.isfinite(float(confianca))
                    or confianca < CONFIANCA_KEYPOINT
                ):
                    return None, None, None

        for ponto in pontos:
            if not all(
                math.isfinite(float(valor))
                for valor in ponto[:2]
            ):
                return None, None, None

        ombro_esq, ombro_dir, quadril_esq, quadril_dir = pontos

        centro_ombros = (
            (ombro_esq[0] + ombro_dir[0]) / 2,
            (ombro_esq[1] + ombro_dir[1]) / 2,
        )
        centro_quadris = (
            (quadril_esq[0] + quadril_dir[0]) / 2,
            (quadril_esq[1] + quadril_dir[1]) / 2,
        )

        dx = centro_ombros[0] - centro_quadris[0]
        dy = centro_ombros[1] - centro_quadris[1]

        if math.hypot(dx, dy) < 1:
            return None, None, None

        angulo = math.degrees(math.atan2(dy, dx))
        desvio_vertical = abs(abs(angulo) - 90.0)

        return desvio_vertical, centro_ombros, centro_quadris

    def avaliar_pessoa(
        self,
        track_id,
        angulo,
        centro_corpo_y,
        altura_frame,
        agora,
    ):
        """Avalia o histórico temporal individual da pessoa."""
        estado = self.estados.setdefault(track_id, EstadoPessoa())
        estado.ultimo_visto = agora

        suspeita = angulo >= ANGULO_SUSPEITO
        ereto = angulo <= ANGULO_ERETO

        estado.posturas_suspeitas.append(suspeita)
        estado.historico_ereto.append(ereto)

        if ereto:
            estado.centro_y_referencia = centro_corpo_y
            estado.frames_recuperacao += 1
        else:
            estado.frames_recuperacao = 0

        # Permite um novo alerta após recuperação observada.
        if estado.frames_recuperacao >= FRAMES_RECUPERACAO:
            estado.alerta_enviado = False

        if len(estado.posturas_suspeitas) < TAMANHO_BUFFER:
            return False

        proporcao = (
            sum(estado.posturas_suspeitas) / TAMANHO_BUFFER
        )

        houve_postura_ereta = any(estado.historico_ereto)

        deslocamento_suficiente = False

        if estado.centro_y_referencia is not None:
            deslocamento = abs(
                centro_corpo_y - estado.centro_y_referencia
            )
            deslocamento_suficiente = (
                deslocamento >= altura_frame * 0.04
            )

        evento_suspeito = (
            proporcao >= PROPORCAO_SUSPEITA
            and houve_postura_ereta
            and deslocamento_suficiente
            and not estado.alerta_enviado
        )

        if evento_suspeito:
            estado.alerta_enviado = True
            return True

        return False

    def executar_monitoramento(
        self,
        atualizar_frame_gui=None,
        verificar_parada=None,
    ):
        """
        Executa o monitoramento.
        A câmera é liberada no finally, inclusive em caso de erro.
        """
        self.is_running = True
        self.estados.clear()
        cap = None

        try:
            if self.parada_solicitada(verificar_parada):
                return

            self.log("[INFO] Carregando modelo YOLO Pose...")
            modelo = YOLO(localizar_modelo())

            # O modelo pode demorar a carregar; confira a parada depois.
            if self.parada_solicitada(verificar_parada):
                return

            self.log("[INFO] Conectando à câmera...")
            cap = cv2.VideoCapture(0)

            if not cap.isOpened():
                raise RuntimeError(
                    "Não foi possível acessar a câmera."
                )

            # Reduz o acúmulo de frames, quando suportado pelo backend.
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            self.log("[INFO] Monitoramento iniciado.")

            while not self.parada_solicitada(verificar_parada):
                sucesso, frame = cap.read()

                # Se a parada foi solicitada durante a leitura, saia.
                if self.parada_solicitada(verificar_parada):
                    break

                if not sucesso:
                    self.log(
                        "[ERRO] Não foi possível ler a câmera."
                    )
                    break

                agora = time.monotonic()
                altura_frame = frame.shape[0]

                resultados = modelo.track(
                    frame,
                    persist=True,
                    conf=CONFIANCA_DETECCAO,
                    verbose=False,
                )

                # Fundamental: não processe nem desenhe se pediram parada
                # enquanto o YOLO estava executando a inferência.
                if self.parada_solicitada(verificar_parada):
                    break

                if not resultados:
                    frame_plotado = frame.copy()
                else:
                    frame_plotado = resultados[0].plot()

                for resultado in resultados:
                    if self.parada_solicitada(verificar_parada):
                        break

                    if (
                        resultado.boxes is None
                        or resultado.keypoints is None
                    ):
                        continue

                    boxes = resultado.boxes
                    keypoints_data = resultado.keypoints.data

                    for i in range(len(boxes)):
                        if self.parada_solicitada(verificar_parada):
                            break

                        # Classe 0 do modelo COCO corresponde a pessoa.
                        if int(boxes.cls[i].item()) != 0:
                            continue

                        x1, y1, x2, y2 = map(
                            int,
                            boxes.xyxy[i].cpu().numpy(),
                        )

                        if not self.caixa_eh_valida(
                            x1, y1, x2, y2
                        ):
                            continue

                        pontos = keypoints_data[i].cpu().numpy()

                        inclinacao, ombros, quadris = (
                            self.calcular_inclinacao(pontos)
                        )

                        if inclinacao is None:
                            continue

                        cor = (
                            (0, 0, 255)
                            if inclinacao >= ANGULO_SUSPEITO
                            else (0, 255, 0)
                        )

                        texto = f"POSTURA: {inclinacao:.1f} graus"

                        # O histórico é separado por pessoa rastreada.
                        if boxes.id is not None:
                            valor_id = boxes.id[i].item()

                            if math.isfinite(float(valor_id)):
                                track_id = int(valor_id)
                                centro_y = (y1 + y2) / 2

                                confirmado = self.avaliar_pessoa(
                                    track_id,
                                    inclinacao,
                                    centro_y,
                                    altura_frame,
                                    agora,
                                )

                                texto = (
                                    f"ID {track_id} | "
                                    f"{inclinacao:.1f} graus"
                                )

                                if confirmado:
                                    texto = (
                                        f"QUEDA | ID {track_id}"
                                    )

                                    horario = time.strftime(
                                        "%d/%m/%Y %H:%M:%S"
                                    )

                                    self.log(
                                        "[ALERTA] Queda "
                                        f"detectada | ID {track_id} "
                                        f"| Horário: {horario}"
                                    )

                        cv2.putText(
                            frame_plotado,
                            texto,
                            (max(5, x1), max(20, y1 - 10)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.55,
                            cor,
                            2,
                        )

                        if ombros is not None and quadris is not None:
                            cv2.line(
                                frame_plotado,
                                tuple(map(int, ombros)),
                                tuple(map(int, quadris)),
                                (255, 0, 0),
                                2,
                            )

                if self.parada_solicitada(verificar_parada):
                    break

                # Remove pessoas que desapareceram por tempo excessivo.
                expirados = [
                    track_id
                    for track_id, estado in self.estados.items()
                    if (
                        agora - estado.ultimo_visto
                        > TEMPO_EXPIRACAO_TRACK
                    )
                ]

                for track_id in expirados:
                    del self.estados[track_id]

                if atualizar_frame_gui:
                    atualizar_frame_gui(frame_plotado)

        except Exception as erro:
            self.log(
                f"[ERRO] Monitoramento interrompido: {erro}"
            )

        finally:
            if cap is not None:
                cap.release()

            self.is_running = False
            self.log("[INFO] Monitoramento encerrado.")
