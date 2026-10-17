
import os
import sys
import queue
import threading
import subprocess

import cv2
from PIL import Image
import customtkinter as ctk

from main import DetectorQuedas
from logs import registrar_log as registrar_log_arquivo


ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class AppMonitoramento(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Sistema de Monitoramento Inteligente")
        self.geometry("980x620")
        self.resizable(False, False)

        self.is_monitoring = False
        self.reinicio_pendente = False
        self.fechando = False
        self.detector = None
        self.thread_execucao = None
        self._imagem_video = None

        self.fila_logs = queue.Queue()
        self.fila_frames = queue.Queue(maxsize=1)

        self.protocol("WM_DELETE_WINDOW", self.fechar_aplicacao)

        self.container = ctk.CTkFrame(
            self,
            fg_color="transparent",
        )
        self.container.pack(fill="both", expand=True)

        self.mostrar_tela_inicial()
        self.after(50, self.processar_filas_ui)

    def limpar_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()

        self._imagem_video = None

    def adicionar_log_ui(self, caixa, mensagem):
        """Permite escrita apenas durante a inserção programática."""
        if not caixa.winfo_exists():
            return

        caixa.configure(state="normal")
        caixa.insert("end", mensagem + "\n")
        caixa.see("end")
        caixa.configure(state="disabled")

    def registrar_log_inicio(self, mensagem):
        registrar_log_arquivo(mensagem)
        self.fila_logs.put(mensagem)

    def registrar_log(self, mensagem):
        """Chamado pelo detector; não altera widgets nesta thread."""
        self.fila_logs.put(mensagem)

    def abrir_arquivo_logs(self):
        caminho = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "logs_quedas.txt",
            )
        )

        if not os.path.exists(caminho):
            with open(caminho, "w", encoding="utf-8") as arquivo:
                arquivo.write("Histórico de monitoramento.\n")

        try:
            if sys.platform == "win32":
                os.startfile(caminho)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", caminho])
            else:
                subprocess.Popen(["xdg-open", caminho])

        except Exception as erro:
            self.registrar_log_inicio(
                f"[ERRO] Falha ao abrir logs: {erro}"
            )

    def mostrar_tela_inicial(self):
        self.limpar_container()

        esquerda = ctk.CTkFrame(
            self.container,
            fg_color="transparent",
        )
        esquerda.pack(
            side="left",
            fill="both",
            expand=True,
            padx=30,
            pady=30,
        )

        ctk.CTkLabel(
            esquerda,
            text="Monitoramento Inteligente",
            font=ctk.CTkFont(
                family="Roboto",
                size=30,
                weight="bold",
            ),
        ).pack(anchor="w", pady=(10, 10))

        ctk.CTkLabel(
            esquerda,
            text=(
                "Protótipo assistivo voltado à segurança de idosos,\n"
                "com visão computacional e YOLOv8 Pose para analisar\n"
                "posturas corporais e identificar possíveis quedas.\n\n"
                "O objetivo é avaliar a detecção automatizada de quedas\n"
                "em cenários residenciais simulados, apoiando estudos\n"
                "sobre monitoramento e prevenção de riscos.\n\n"
                "Clique abaixo para iniciar o monitoramento."
            ),
            font=ctk.CTkFont(size=15),
            text_color="gray",
            justify="left",
        ).pack(anchor="w", pady=(0, 20))

        botoes = ctk.CTkFrame(
            esquerda,
            fg_color="transparent",
        )
        botoes.pack(side="bottom", anchor="w", fill="x", pady=(0, 10))

        ctk.CTkButton(
            botoes,
            text="Iniciar Monitoramento",
            width=210,
            height=40,
            command=self.iniciar_monitoramento,
        ).pack(side="left", padx=(0, 15))

        ctk.CTkButton(
            botoes,
            text="Abrir Logs TXT",
            width=200,
            height=40,
            command=self.abrir_arquivo_logs,
        ).pack(side="left")

        direita = ctk.CTkFrame(
            self.container,
            width=300,
            corner_radius=12,
        )
        direita.pack(
            side="right",
            fill="y",
            padx=20,
            pady=20,
        )
        direita.pack_propagate(False)

        ctk.CTkLabel(
            direita,
            text="Painel de Alertas",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=15, pady=(15, 8))

        self.txt_logs_inicio = ctk.CTkTextbox(
            direita,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color="#141414",
            text_color="#2980b9",
        )
        self.txt_logs_inicio.pack(
            padx=15,
            pady=(0, 15),
            fill="both",
            expand=True,
        )
        self.txt_logs_inicio.configure(state="disabled")

        self.adicionar_log_ui(
            self.txt_logs_inicio,
            "[INFO] Interface gráfica carregada.",
        )
        self.adicionar_log_ui(
            self.txt_logs_inicio,
            "[INFO] Aguardando operador.",
        )

    def iniciar_monitoramento(self):
        """Inicia o detector sem bloquear a interface."""
        if self.fechando or self.is_monitoring:
            return

        if self.thread_execucao is not None:
            if self.thread_execucao.is_alive():
                self.reinicio_pendente = True
                self.registrar_log_inicio(
                    "[INFO] Reinício solicitado. Aguardando liberação da câmera..."
                )
                return
            # Limpa a sessão já encerrada antes de abrir outra.
            self.finalizar_monitoramento()

        self.reinicio_pendente = False
        self.limpar_container()
        self.is_monitoring = True

        esquerda = ctk.CTkFrame(
            self.container,
            fg_color="transparent",
        )
        esquerda.pack(
            side="left",
            fill="both",
            expand=True,
            padx=30,
            pady=30,
        )

        ctk.CTkLabel(
            esquerda,
            text="Monitoramento Inteligente",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(anchor="w", pady=(5, 8))

        self.lbl_video = ctk.CTkLabel(
            esquerda,
            text="Carregando câmera...",
            fg_color="#1a1a1a",
            corner_radius=10,
            width=560,
            height=390,
        )
        self.lbl_video.pack(anchor="w", pady=5)

        botoes = ctk.CTkFrame(
            esquerda,
            fg_color="transparent",
        )
        botoes.pack(
            side="bottom",
            anchor="w",
            fill="x",
            pady=(0, 10),
        )

        self.btn_parar = ctk.CTkButton(
            botoes,
            text="Encerrar Monitoramento",
            width=210,
            height=40,
            fg_color="#b8860b",
            hover_color="#8b6508",
            command=self.parar_monitoramento,
        )
        self.btn_parar.pack(side="left", padx=(0, 15))

        ctk.CTkButton(
            botoes,
            text="Abrir Logs TXT",
            width=160,
            height=40,
            command=self.abrir_arquivo_logs,
        ).pack(side="left")

        direita = ctk.CTkFrame(
            self.container,
            width=300,
            corner_radius=12,
        )
        direita.pack(
            side="right",
            fill="y",
            padx=20,
            pady=20,
        )
        direita.pack_propagate(False)

        ctk.CTkLabel(
            direita,
            text="Status do Sistema",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=15, pady=(15, 8))

        self.txt_monitor_logs = ctk.CTkTextbox(
            direita,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color="#141414",
            text_color="#2980b9",
        )
        self.txt_monitor_logs.pack(
            padx=15,
            pady=(0, 15),
            fill="both",
            expand=True,
        )
        self.txt_monitor_logs.configure(state="disabled")

        self.detector = DetectorQuedas(
            callback_log=self.registrar_log,
        )

        # A thread recebe a função que verifica se o operador pediu parada.
        self.thread_execucao = threading.Thread(
            target=self.detector.executar_monitoramento,
            args=(
                self.atualizar_frame_ui,
                self.parada_solicitada,
            ),
            name="thread-monitoramento",
            daemon=True,
        )
        self.thread_execucao.start()

    def parada_solicitada(self):
        """Consulta a solicitação de parada da interface."""
        return not self.is_monitoring or self.fechando

    def atualizar_frame_ui(self, frame_cv2):
        """Guarda apenas o frame mais recente."""
        try:
            self.fila_frames.put_nowait(frame_cv2.copy())
        except queue.Full:
            try:
                self.fila_frames.get_nowait()
            except queue.Empty:
                pass

            try:
                self.fila_frames.put_nowait(frame_cv2.copy())
            except queue.Full:
                pass

    def processar_filas_ui(self):
        """Atualiza widgets exclusivamente na thread principal."""
        if self.fechando:
            return

        # Processa todos os logs pendentes.
        while True:
            try:
                mensagem = self.fila_logs.get_nowait()
            except queue.Empty:
                break

            if (
                hasattr(self, "txt_monitor_logs")
                and self.txt_monitor_logs.winfo_exists()
            ):
                self.adicionar_log_ui(
                    self.txt_monitor_logs,
                    mensagem,
                )
            elif (
                hasattr(self, "txt_logs_inicio")
                and self.txt_logs_inicio.winfo_exists()
            ):
                self.adicionar_log_ui(
                    self.txt_logs_inicio,
                    mensagem,
                )

        # Recupera somente o frame mais recente.
        frame = None
        while True:
            try:
                frame = self.fila_frames.get_nowait()
            except queue.Empty:
                break

        if (
            frame is not None
            and self.is_monitoring
            and hasattr(self, "lbl_video")
            and self.lbl_video.winfo_exists()
        ):
            try:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                imagem = Image.fromarray(rgb).resize((560, 390))

                self._imagem_video = ctk.CTkImage(
                    light_image=imagem,
                    dark_image=imagem,
                    size=(560, 390),
                )
                self.lbl_video.configure(
                    image=self._imagem_video,
                    text="",
                )
            except Exception as erro:
                self.fila_logs.put(
                    f"[ERRO] Falha ao exibir o vídeo: {erro}"
                )

        # Limpa sessões encerradas, inclusive após o retorno imediato.
        if (
            self.thread_execucao is not None
            and not self.thread_execucao.is_alive()
        ):
            self.finalizar_monitoramento()

        self.after(50, self.processar_filas_ui)

    def parar_monitoramento(self):
        """Volta à tela inicial sem aguardar a liberação da câmera."""
        if not self.is_monitoring:
            return

        self.is_monitoring = False
        self.reinicio_pendente = False

        if self.detector is not None:
            self.detector.parar()

        # Navegação imediata; o loop da interface acompanhará a thread.
        self.mostrar_tela_inicial()

    def verificar_encerramento(self):
        """Compatibilidade: verifica a conclusão sem bloquear a interface."""
        if self.fechando:
            return
        if self.thread_execucao is not None and not self.thread_execucao.is_alive():
            self.finalizar_monitoramento()

    def finalizar_monitoramento(self):
        """Libera referências somente depois do término da thread."""
        if self.thread_execucao is not None and self.thread_execucao.is_alive():
            return

        havia_monitoramento_ativo = self.is_monitoring
        reiniciar = self.reinicio_pendente
        self.reinicio_pendente = False
        self.is_monitoring = False
        self.thread_execucao = None
        self.detector = None

        while True:
            try:
                self.fila_frames.get_nowait()
            except queue.Empty:
                break

        if self.fechando:
            return

        if havia_monitoramento_ativo:
            # Término natural ou erro na câmera.
            self.mostrar_tela_inicial()

        if reiniciar:
            self.after(0, self.iniciar_monitoramento)

    def fechar_aplicacao(self):
        """Fecha a aplicação solicitando a parada do detector."""
        self.fechando = True
        self.is_monitoring = False
        self.reinicio_pendente = False

        if self.detector is not None:
            self.detector.parar()

        # Não bloqueia indefinidamente a thread da interface.
        self.destroy()


if __name__ == "__main__":
    app = AppMonitoramento()
    app.mainloop()
