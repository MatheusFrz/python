# -*- coding: utf-8 -*-
"""
Created on Mon Mar 18 23:45:03 2024
@author: Jonas

Ponto de entrada do programa.
"""

import tkinter as tk
import cv2

import config
from selecao_video import selecionar_arquivo_video, nome_base
from video_utils import (
    abrir_video,
    dimensoes_video,
    calcular_escala_exibicao,
    dimensoes_exibicao,
    bbox_exibicao_para_original,
)
from rastreador import RastreadorKCF, desenhar_bbox
from conversao import bbox_para_metros
from exportador_csv import ExportadorCSV


def main():
    caminho_video = selecionar_arquivo_video()
    nome = nome_base(caminho_video)

    # dimensões da tela do usuário, para a janela de exibição caber nela
    root = tk.Tk()
    largura_tela = root.winfo_screenwidth()
    altura_tela = root.winfo_screenheight()
    root.destroy()

    cap = abrir_video(caminho_video)
    largura_video, altura_video = dimensoes_video(cap)

    escala = calcular_escala_exibicao(
        largura_video, altura_video, largura_tela, altura_tela, config.MARGEM_TELA
    )
    nova_largura, nova_altura = dimensoes_exibicao(largura_video, altura_video, escala)

    # atraso entre frames na tela, só pra exibição — não influencia tempo_acumulado
    delay_exibicao_ms = max(1, int(1000 * config.TEMPO_S * config.FATOR_LENTIDAO_EXIBICAO))

    try:
        ret, frame = cap.read()
        if not ret:
            raise SystemExit("Não foi possível ler o primeiro frame do vídeo.")

        frame_selecao = cv2.resize(frame, (nova_largura, nova_altura))
        bbox_roi_exibicao = cv2.selectROI(
            "Selecione o objeto a ser rastreado", frame_selecao, fromCenter=False, showCrosshair=True
        )
        cv2.destroyWindow("Selecione o objeto a ser rastreado")
        bbox_roi = bbox_exibicao_para_original(bbox_roi_exibicao, escala)
        rastreador = RastreadorKCF(frame, bbox_roi)

        with ExportadorCSV(nome + " - posicoes.csv") as exportador:
            tempo_acumulado = 0.0

            while True:
                ret, frame = cap.read()
                if not ret:
                    break  # encerra ao chegar no último frame

                tempo_acumulado += config.TEMPO_S
                sucesso, bbox = rastreador.atualizar(frame)

                if sucesso:
                    desenhar_bbox(frame, bbox)
                    x_m, y_m = bbox_para_metros(
                        bbox,
                        altura_video,
                        rastreador.largura_roi,
                        rastreador.altura_roi,
                        config.RAIO_M,
                    )
                    exportador.registrar(tempo_acumulado, x_m, y_m)

                frame_exibicao = cv2.resize(frame, (nova_largura, nova_altura))
                cv2.imshow("Rastreamento de Objeto", frame_exibicao)
                if cv2.waitKey(delay_exibicao_ms) & 0xFF == ord('q'):
                    break
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
