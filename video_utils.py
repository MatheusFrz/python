# -*- coding: utf-8 -*-
"""
Tudo relacionado a abrir o vídeo e calcular como exibi-lo na tela.
"""

import cv2


def abrir_video(caminho_video: str) -> cv2.VideoCapture:
    """Abre o vídeo e valida se foi carregado corretamente."""
    cap = cv2.VideoCapture(caminho_video)
    if not cap.isOpened():
        raise SystemExit("Nenhum vídeo selecionado ou arquivo inválido.")
    return cap


def dimensoes_video(cap: cv2.VideoCapture) -> tuple[float, float]:
    """Retorna (largura, altura) originais do vídeo, em pixels."""
    largura = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    altura = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    return largura, altura


def calcular_escala_exibicao(
    largura_video: float,
    altura_video: float,
    largura_tela: int,
    altura_tela: int,
    margem: float,
) -> float:
    """
    Calcula a escala para que o vídeo caiba na tela sem distorcer
    a proporção original e sem jamais ser ampliado (só reduzido).
    """
    escala = min(
        (largura_tela * margem) / largura_video,
        (altura_tela * margem) / altura_video,
    )
    return min(escala, 1.0)


def dimensoes_exibicao(largura_video: float, altura_video: float, escala: float) -> tuple[int, int]:
    """Converte largura/altura originais para as dimensões de exibição."""
    return int(largura_video * escala), int(altura_video * escala)


def bbox_exibicao_para_original(
    bbox_exibicao: tuple[float, float, float, float], escala: float
) -> tuple[float, float, float, float]:
    """
    Converte uma bbox selecionada na janela redimensionada (escala de
    exibição) de volta para as coordenadas do vídeo em resolução original.
    """
    return tuple(valor / escala for valor in bbox_exibicao)
