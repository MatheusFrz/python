# -*- coding: utf-8 -*-
"""
rastreador.py - segue o objeto de um frame para o outro.

Papel:
    Encapsula o tracker KCF do OpenCV. O resto do programa não precisa
    saber como o KCF funciona: cria-se um RastreadorKCF com o primeiro frame
    e a caixa do objeto, e depois chama-se atualizar() a cada novo frame.

Convenção de caixa ("bbox"): tupla (x, y, largura, altura) em pixels, com
(x, y) no canto superior esquerdo. Esta é a convenção do OpenCV.

Usado por: main.py.
"""

import cv2


class RastreadorKCF:
    def __init__(self, frame_inicial, bbox_roi):
        """
        Parâmetros:
            frame_inicial: primeiro frame, com o objeto na posição marcada.
            bbox_roi: caixa do objeto nesse frame (pode ser float).
        """
        self.tracker = cv2.TrackerKCF_create()
        # O tracker exige pixels inteiros; a caixa pode chegar em float por
        # causa das conversões de escala painel -> original.
        self.bbox_inicial = tuple(int(round(valor)) for valor in bbox_roi)
        self.tracker.init(frame_inicial, self.bbox_inicial)

    # A largura e a altura da caixa INICIAL são a régua da medição: servem de
    # referência fixa para converter pixels em metros em todos os frames
    # (ver conversao.py).
    @property
    def largura_roi(self) -> float:
        return self.bbox_inicial[2]

    @property
    def altura_roi(self) -> float:
        return self.bbox_inicial[3]

    def atualizar(self, frame):
        """
        Procura o objeto no frame atual.
        Retorna (sucesso, bbox): sucesso é False se o tracker perdeu o objeto.
        """
        return self.tracker.update(frame)


def desenhar_bbox(frame, bbox, cor=(0, 255, 0), espessura=2):
    """Desenha a caixa sobre o frame (modifica o frame), para feedback visual."""
    x, y, w, h = bbox
    cv2.rectangle(frame, (int(x), int(y)), (int(x + w), int(y + h)), cor, espessura)