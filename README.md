# Sistema de Monitoramento Inteligente
**Trabalho de Conclusão de Curso (TCC)**

**Autor:** Roger Vidal

## 1. Objetivo

O Sistema de Monitoramento Inteligente é um protótipo assistivo desenvolvido em Python, voltado ao monitoramento de pessoas, especialmente idosos, por meio de visão computacional e inteligência artificial.

O objetivo principal é identificar situações compatíveis com possíveis quedas utilizando o modelo YOLOv8-Pose, responsável pela detecção de pessoas e estimativa de pontos corporais (*keypoints*).

A aplicação analisa a inclinação do tronco, o histórico de posturas e o deslocamento vertical da pessoa para identificar eventos suspeitos.

O projeto possui finalidade acadêmica e experimental, buscando contribuir para estudos relacionados à segurança, ao monitoramento assistivo e à prevenção de riscos.

## 2. Tecnologias utilizadas

| Tecnologia | Finalidade |
|---|---|
| Python | Linguagem principal de desenvolvimento |
| YOLOv8n-Pose | Detecção de pessoas e estimativa de pose corporal |
| Ultralytics | Execução do modelo YOLO |
| OpenCV | Captura e processamento dos frames da câmera |
| CustomTkinter | Desenvolvimento da interface gráfica |
| Pillow | Conversão e manipulação das imagens exibidas |
| Threading | Execução do monitoramento sem bloquear a interface |
| Queue | Comunicação entre processamento e interface |
| Logging | Registro de eventos, alertas e erros |
| Math | Cálculo da inclinação corporal |

## 3. Funcionalidades

- Captura de vídeo por câmera conectada ao computador.
- Detecção de pessoas utilizando YOLOv8n-Pose.
- Identificação de pontos corporais, como ombros e quadris.
- Cálculo da inclinação do tronco em relação à vertical.
- Rastreamento individual de pessoas.
- Análise temporal das posturas detectadas.
- Verificação de deslocamento vertical.
- Identificação de possíveis quedas.
- Registro de alertas com identificador e horário.
- Visualização do monitoramento em interface gráfica.
- Consulta ao histórico de eventos em arquivo TXT.
- Inicialização e encerramento do monitoramento pela interface.

## 4. Estrutura do projeto

A organização considerada para a execução é:

```text
monitoramento-inteligente/
│
├── src/
│   ├── app.py
│   ├── main.py
│   └── logs.py
│
├── yolov8n-pose.pt
├── logs_quedas.txt
└── README.md
```

**Descrição dos arquivos:**

- `app.py`: interface gráfica e gerenciamento do monitoramento.
- `main.py`: processamento de imagens, análise corporal e identificação de possíveis quedas.
- `logs.py`: gerenciamento dos registros de eventos.
- `yolov8n-pose.pt`: pesos do modelo de inteligência artificial.
- `logs_quedas.txt`: histórico gerado durante a utilização do sistema.

O arquivo de pesos pode ser localizado automaticamente pelo Ultralytics, inclusive por download quando necessário. O arquivo de logs é criado durante a execução.

## 5. Requisitos

Para executar a aplicação, são necessários:

- Python 3.10 ou superior, como versão recomendada.
- Webcam integrada ou externa.
- Sistema operacional compatível com Python, OpenCV e Tkinter.
- Conexão com a internet para obter dependências e, se necessário, os pesos do modelo.
- Hardware com capacidade suficiente para executar a inferência do YOLO.

## 6. Instalação

### 6.1. Obter o projeto

Após baixar ou clonar o repositório, acessar a pasta principal:

```bash
cd monitoramento-inteligente
```

### 6.2. Criar um ambiente virtual

No Windows:

```bash
python -m venv venv
```

Ativar o ambiente virtual:

```bash
venv\Scripts\activate
```

No Linux ou macOS:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 6.3. Instalar as dependências

Executar:

```bash
python -m pip install ultralytics opencv-python customtkinter pillow
```

As dependências adicionais necessárias ao Ultralytics serão resolvidas pelo gerenciador de pacotes, conforme a plataforma.

### 6.4. Preparar o modelo YOLO

A implementação utiliza o modelo:

```text
yolov8n-pose.pt
```

O arquivo pode ser colocado na pasta `src/` ou na raiz do projeto.

Caso não esteja disponível localmente, o Ultralytics poderá tentar obtê-lo automaticamente.

## 7. Execução

Com o ambiente virtual ativado e as dependências instaladas, executar na raiz do projeto:

```bash
python src/app.py
```

Caso os três arquivos Python estejam diretamente na pasta principal, utilizar:

```bash
python app.py
```

Após a execução, será exibida a interface gráfica do Sistema de Monitoramento Inteligente.

### Utilização

1. Selecionar **Iniciar Monitoramento**.
2. Aguardar o carregamento do modelo YOLO e a conexão com a câmera.
3. Observar as pessoas detectadas e os pontos corporais apresentados no vídeo.
4. Acompanhar as mensagens no painel de status.
5. Consultar os registros utilizando **Abrir Logs TXT**.
6. Selecionar **Encerrar Monitoramento** para interromper a análise.

## 8. Lógica de detecção

O processo de identificação de possíveis quedas ocorre em quatro etapas principais.

**1. Detecção de pessoas:** o YOLOv8n-Pose identifica pessoas presentes na imagem e estima seus pontos corporais.

**2. Análise postural:** o algoritmo utiliza os pontos dos ombros e quadris para calcular a inclinação do tronco em relação à vertical.

**3. Análise temporal:** são avaliadas as posturas recentes de cada pessoa, verificando a persistência da inclinação, a existência de uma postura ereta anterior e o deslocamento vertical.

**4. Registro do alerta:** quando todos os critérios definidos são atendidos, o sistema registra uma possível queda no painel de status e no arquivo de histórico.

### Parâmetros principais

| Parâmetro | Valor |
|---|---|
| Confiança mínima de detecção | 65% |
| Confiança mínima dos keypoints | 45% |
| Ângulo de postura suspeita | 60° ou superior |
| Ângulo de postura ereta | 30° ou inferior |
| Janela temporal | 15 avaliações |
| Proporção mínima de posturas suspeitas | 80% |
| Recuperação para novo alerta | 10 avaliações eretas consecutivas |
| Expiração de rastreamento | 3 segundos |
| Deslocamento vertical mínimo | 4% da altura do frame |

Esses valores correspondem às configurações atuais do protótipo e podem ser ajustados no código após avaliação experimental.

## 9. Registro de eventos

O sistema utiliza o arquivo `logs_quedas.txt` para armazenar informações sobre o funcionamento e os alertas identificados.

Exemplo ilustrativo:

```text
16/10/2026 20:37:24 | INFO | [INFO] Monitoramento iniciado.
16/10/2026 20:38:06 | WARNING | [ALERTA] Queda detectada | ID 1 | Horário: 16/10/2026 20:38:06
```

Os registros permitem acompanhar eventos ocorridos durante a execução e auxiliam na análise dos testes.

## 10. Limitações

O sistema encontra-se em fase de prototipagem acadêmica.

A identificação de possíveis quedas é baseada em regras geométricas e temporais e pode ser afetada por iluminação, oclusões, posicionamento da câmera, movimentações voluntárias e mudanças nos identificadores das pessoas rastreadas.

A implementação não garante a identificação de todas as quedas nem a ausência de falsos positivos.

O protótipo não substitui a supervisão humana, dispositivos médicos ou sistemas profissionais de emergência.

## 11. Melhorias futuras

Entre as possibilidades de evolução estão:

- Configuração dos parâmetros diretamente pela interface.
- Envio de notificações automáticas.
- Integração com aplicativos móveis.
- Armazenamento estruturado de ocorrências.
- Geração de relatórios e gráficos.
- Suporte a múltiplas câmeras.
- Aperfeiçoamento da análise temporal.
- Testes com bases de vídeos rotulados.
- Avaliação de precisão, sensibilidade e taxa de falsos positivos.

## 12. Autoria e finalidade acadêmica

**Desenvolvimento:** Roger Vidal

**Projeto:** Sistema de Monitoramento Inteligente — Detecção de Quedas

**Finalidade:** Trabalho de Conclusão de Curso (TCC)

**Data da documentação:** 16 de outubro de 2026

O projeto foi desenvolvido com finalidade acadêmica, visando explorar a aplicação de técnicas de inteligência artificial e visão computacional no monitoramento assistivo de pessoas e na identificação de possíveis situações de risco.
