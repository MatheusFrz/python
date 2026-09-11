# -*- coding: utf-8 -*-
"""
Encapsula tudo relacionado ao tracker: inicialização e atualização
quadro a quadro.
"""

import cv2


class RastreadorKCF:
    def __init__(self, frame_inicial, bbox_roi):
        self.tracker = cv2.TrackerKCF_create()
        # o tracker exige coordenadas de pixel inteiras — bbox_roi pode
        # chegar em float quando vem de uma conversão de escala de exibição
        self.bbox_inicial = tuple(int(round(valor)) for valor in bbox_roi)
        self.tracker.init(frame_inicial, self.bbox_inicial)

    @property
    def largura_roi(self) -> float:
        return self.bbox_inicial[2]

    @property
    def altura_roi(self) -> float:
        return self.bbox_inicial[3]

    def atualizar(self, frame):
        """Atualiza o tracker para o frame atual. Retorna (sucesso, bbox)."""
        return self.tracker.update(frame)


def desenhar_bbox(frame, bbox, cor=(0, 255, 0), espessura=2):
    """Desenha a bbox atual sobre o frame, para feedback visual."""
    x, y, w, h = bbox
    cv2.rectangle(frame, (int(x), int(y)), (int(x + w), int(y + h)), cor, espessura)
