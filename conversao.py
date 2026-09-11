# -*- coding: utf-8 -*-
"""
Conversão de coordenadas de pixels (origem no canto superior esquerdo,
Y crescendo para baixo) para metros (origem no canto inferior esquerdo,
Y crescendo para cima), usando a ROI inicial como referência de escala.
"""


def bbox_para_metros(
    bbox: tuple[float, float, float, float],
    altura_video: float,
    largura_roi: float,
    altura_roi: float,
    raio_m: float,
) -> tuple[float, float]:
    """Converte o centro da bbox (em pixels) para coordenadas em metros."""
    x, y, w, h = bbox

    escala_x = raio_m / largura_roi
    escala_y = raio_m / altura_roi

    x_m = (x + w / 2) * escala_x
    y_m = (altura_video - (y + h / 2)) * escala_y

    return x_m, y_m
