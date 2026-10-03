# -*- coding: utf-8 -*-
"""
video_utils.py - ajuste do frame ao painel e conversão de coordenadas.

Papel:
    Funções puras (sem estado) sobre dimensões e coordenadas. Duas ideias
    centrais:
        1. Encaixar o frame no painel SEM distorcer
               -> ajustar_ao_painel
        2. Converter pontos entre o painel e o vídeo original
               -> painel_para_original / original_para_painel

Vocabulário de coordenadas (vale para o projeto inteiro):
    "original" = pixels do vídeo em resolução real. É onde o rastreador
                 trabalha e de onde saem as medidas em metros.
    "painel"   = pixels da área de vídeo na janela. É menor que o original e
                 tem barras pretas quando as proporções diferem.

Usado por: main.py, interface.py.

Obs.: abrir_video, calcular_escala_exibicao, dimensoes_exibicao e
bbox_exibicao_para_original vêm da versão antiga (janela do OpenCV com
cv2.selectROI) e não são mais chamadas. Foram mantidas aqui; podem ser
removidas sem afetar o programa.
"""

import cv2
import numpy as np


# ======================================================================
# ABERTURA E DIMENSÕES DO VÍDEO
# ======================================================================

def abrir_video(caminho_video: str) -> cv2.VideoCapture:
    """(Sem uso atual.) Abre o vídeo e encerra o programa se não abrir."""
    cap = cv2.VideoCapture(caminho_video)
    if not cap.isOpened():
        raise SystemExit("Nenhum vídeo selecionado ou arquivo inválido.")
    return cap


def dimensoes_video(cap: cv2.VideoCapture) -> tuple[float, float]:
    """Retorna (largura, altura) do vídeo, em pixels originais."""
    largura = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    altura = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    return largura, altura


# ======================================================================
# VERSÃO ANTIGA (janela do OpenCV) - sem uso atual
# ======================================================================

def calcular_escala_exibicao(
    largura_video: float,
    altura_video: float,
    largura_tela: int,
    altura_tela: int,
    margem: float,
) -> float:
    """
    (Sem uso atual.) Escala para o vídeo caber na tela, sem distorcer a
    proporção e sem nunca ampliar (só reduz).
    """
    escala = min(
        (largura_tela * margem) / largura_video,
        (altura_tela * margem) / altura_video,
    )
    return min(escala, 1.0)


def dimensoes_exibicao(largura_video: float, altura_video: float, escala: float) -> tuple[int, int]:
    """(Sem uso atual.) Largura e altura do vídeo depois de aplicar a escala."""
    return int(largura_video * escala), int(altura_video * escala)


def bbox_exibicao_para_original(
    bbox_exibicao: tuple[float, float, float, float], escala: float
) -> tuple[float, float, float, float]:
    """
    (Sem uso atual.) Converte uma caixa (x, y, largura, altura) marcada na
    imagem reduzida de volta para pixels originais.
    """
    return tuple(valor / escala for valor in bbox_exibicao)


# ======================================================================
# AJUSTE AO PAINEL E CONVERSÃO DE COORDENADAS
# ======================================================================

def ajustar_ao_painel(frame, largura_painel: int, altura_painel: int):
    """
    Encaixa o frame num painel de tamanho fixo SEM distorcer.

    Como evita a distorção: usa UMA escala só para largura e altura (a menor
    das duas razões), então a proporção original é preservada. O espaço que
    sobra num dos eixos vira barra preta, e o frame fica centralizado.

    Parâmetros:
        frame: imagem BGR em resolução original.
        largura_painel, altura_painel: tamanho do painel, em pixels.

    Retorna (canvas, escala, (x0, y0)):
        canvas:  imagem do tamanho exato do painel, pronta para exibir.
        escala:  fator original -> painel.
        (x0, y0): canto superior esquerdo do frame dentro do painel, isto é,
                  a largura das barras pretas laterais (x0) e superiores (y0).
    """
    h, w = frame.shape[:2]
    escala = min(largura_painel / w, altura_painel / h)
    largura_redimensionada, altura_redimensionada = round(w * escala), round(h * escala)

    # INTER_AREA dá o melhor resultado ao reduzir; INTER_LINEAR ao ampliar
    interpolacao = cv2.INTER_AREA if escala < 1 else cv2.INTER_LINEAR
    frame_redimensionado = cv2.resize(
        frame, (largura_redimensionada, altura_redimensionada), interpolation=interpolacao
    )

    canvas = np.zeros((altura_painel, largura_painel, 3), dtype=np.uint8)
    x0 = (largura_painel - largura_redimensionada) // 2
    y0 = (altura_painel - altura_redimensionada) // 2
    canvas[y0:y0 + altura_redimensionada, x0:x0 + largura_redimensionada] = frame_redimensionado
    return canvas, escala, (x0, y0)


def painel_para_original(x_painel: float, y_painel: float, escala: float, offset: tuple[int, int]):
    """
    Converte um ponto do painel (ex.: posição do mouse) para o pixel
    correspondente no vídeo original.

    Passos: tira as barras pretas (subtrai o offset) e desfaz a redução
    (divide pela escala). É o inverso de original_para_painel.
    """
    x0, y0 = offset
    return (x_painel - x0) / escala, (y_painel - y0) / escala


def original_para_painel(x: float, y: float, escala: float, offset: tuple[int, int]):
    """
    Converte um ponto do vídeo original para o pixel correspondente no painel
    (aplica a redução e soma as barras pretas). Usado para desenhar a caixa
    detectada sobre o frame exibido.
    """
    x0, y0 = offset
    return x * escala + x0, y * escala + y0