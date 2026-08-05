# -*- coding: utf-8 -*-
"""
Created on Mon Mar 18 23:45:03 2024

@author: Jonas
"""

# -- Imports --
import tkinter as tk
from tkinter import filedialog
from pathlib import Path
import cv2

# -- Parâmetros do experimento --
raio_m = 0.0212   # raio real do objeto rastreado, em metros
tempo_s = 1/120   # intervalo entre frames em segundos (1 / fps do vídeo)

# -- Seleção do vídeo --
root = tk.Tk()
root.withdraw()  # abre o tkinter em segundo plano, apenas para usar o filedialog

# Captura as dimensões da tela do dispositivo para ajuste da janela de exibição
largura_tela = root.winfo_screenwidth()
altura_tela  = root.winfo_screenheight()

video_path = filedialog.askopenfilename(
    title="Selecione o vídeo",
    filetypes=[("Vídeos", "*.mp4 *.avi *.mov *.mkv")]
)
nome = Path(video_path).stem  # extrai o nome do arquivo sem a extensão

# -- Abertura do vídeo e leitura das dimensões originais --
cap = cv2.VideoCapture(video_path)
largura_video = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
altura_video  = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)

# Calcula a escala de exibição para que o vídeo caiba na tela
# sem distorcer a proporção original
margem = 0.85
escala = min(
    (largura_tela * margem) / largura_video,
    (altura_tela  * margem) / altura_video
)
escala = min(escala, 1.0)  # garante que nunca amplie, apenas reduz
nova_largura = int(largura_video * escala)
nova_altura  = int(altura_video  * escala)

try:
    # -- Validação do vídeo selecionado --
    # Interrompe imediatamente se nenhum arquivo foi escolhido ou o vídeo é inválido
    if not cap.isOpened():
        raise SystemExit("Nenhum vídeo selecionado ou arquivo inválido.")

    # -- Inicialização do tracker e leitura do primeiro frame --
    tracker = cv2.TrackerKCF_create()
    ret, frame = cap.read()

    # -- Seleção e fixação da ROI --
    # O usuário delimita o objeto no primeiro frame
    # roi_w e roi_h são fixados aqui e usados como referência de escala em todos os frames
    bbox = cv2.selectROI("Selecione o objeto a ser rastreado", frame, fromCenter=False, showCrosshair=True)
    roi_w = bbox[2]
    roi_h = bbox[3]
    tracker.init(frame, bbox)

    # -- Loop de rastreamento e exportação --
    with open(nome + " - posicoes.csv", "w", newline="", encoding="utf-8") as output_file:
        output_file.write("Tempo,X,Y\n")
        frame_number = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break  # encerra ao chegar no último frame

            frame_number += tempo_s  # acumula o tempo em segundos
            ret, bbox = tracker.update(frame)

            if ret:
                x, y, w, h = bbox
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

                # Converte o centro da bbox de pixels para metros
                # usando roi_w e roi_h fixos para manter a escala constante
                x = (x + w / 2) * (raio_m / roi_w)
                y = (altura_video - (y + h / 2)) * (raio_m / roi_h)
                output_file.write(f"{frame_number},{x},{y}\n")

            # Redimensiona apenas para exibição — os dados originais não são alterados
            frame_exibicao = cv2.resize(frame, (nova_largura, nova_altura))
            cv2.imshow("Rastreamento de Objeto", frame_exibicao)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

# -- Liberação de recursos --
# O bloco finally garante que o vídeo e as janelas sejam fechados em qualquer situação
finally:
    cap.release()
    cv2.destroyAllWindows()