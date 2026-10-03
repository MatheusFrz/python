# -*- coding: utf-8 -*-
"""
conversao.py - de pixels para metros.

Papel:
    Converte a posição do objeto (pixels da imagem) em coordenadas físicas
    (metros), que são o que vai para o CSV e para os gráficos.

Dois sistemas de eixos:
    Imagem (pixels): origem no canto SUPERIOR esquerdo, Y cresce para BAIXO.
    Física (metros): origem no canto INFERIOR esquerdo, Y cresce para CIMA.
    A inversão do eixo Y é feita aqui (altura_video - y).

A régua (escala):
    O programa não sabe quantos metros tem um pixel. Ele assume que a
    LARGURA da caixa marcada no primeiro frame equivale a "raio_objeto_m"
    metros e usa isso como escala:
        metros por pixel = raio_objeto_m / largura_roi

    ATENÇÃO: o valor informado precisa corresponder à dimensão que a caixa
    realmente cobre. Se a caixa envolve o objeto inteiro (como na detecção
    automática), a largura dela é o DIÂMETRO, e é o diâmetro que deveria ser
    informado. Caso contrário, todas as medidas saem na escala errada.

Usado por: main.py.
"""


def bbox_para_metros(
    bbox: tuple[float, float, float, float],
    altura_video: float,
    largura_roi: float,
    altura_roi: float,
    raio_objeto_m: float,
) -> tuple[float, float]:
    """
    Converte o CENTRO da caixa (em pixels) para coordenadas em metros.

    Parâmetros:
        bbox: caixa atual do objeto (x, y, largura, altura), em pixels.
        altura_video: altura do vídeo original, em pixels (para inverter o eixo Y).
        largura_roi, altura_roi: tamanho da caixa INICIAL, em pixels. Ficam
            fixos durante todo o vídeo, para a escala não variar.
        raio_objeto_m: dimensão real, em metros, que a caixa inicial representa.

    Retorna (x_m, y_m).
    """
    x, y, w, h = bbox

    # metros por pixel em cada eixo
    escala_x = raio_objeto_m / largura_roi
    escala_y = raio_objeto_m / altura_roi

    x_m = (x + w / 2) * escala_x                      # centro da caixa, em metros
    y_m = (altura_video - (y + h / 2)) * escala_y     # eixo Y invertido (para cima)

    return x_m, y_m