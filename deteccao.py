# -*- coding: utf-8 -*-
"""
deteccao.py - acha o objeto no primeiro frame, para a marcação ser quase automática.

Papel:
    Entrega a caixa (x, y, largura, altura) do objeto, em pixels do vídeo
    ORIGINAL, que é o formato que o rastreador espera.

Dois métodos, do mais confiável para o menos:
    1. MOVIMENTO
       Mistura vários frames do vídeo (mediana) para obter o "fundo sem o
       objeto". O que difere desse fundo no primeiro frame é o objeto.
       Condições: câmera parada e objeto que se mova durante o vídeo. Se o
       objeto ficar parado em mais da metade do vídeo, ele entra no "fundo"
       e este método não o enxerga.
    2. COR
       Parte do ponto clicado e expande a região de cor parecida.

Duas formas de uso:
    detectar_automatico(frame)         procura o objeto sozinho
    detectar_no_ponto(frame, x, y)     ajusta a caixa ao objeto clicado

Parâmetros de sensibilidade: seção "Detecção automática" do config.py.
Usado por: main.py.
"""

import cv2
import numpy as np

import config

# Atalho para criar o "elemento estruturante" das operações morfológicas
# (abertura e fechamento), que limpam e unem regiões da máscara.
_elemento_estruturante = cv2.getStructuringElement


class DetectorObjeto:
    def __init__(self, caminho_video: str):
        """Prepara o detector: já calcula o fundo a partir do vídeo inteiro."""
        self.fundo_mediano = None   # fundo sem o objeto, em tamanho reduzido
        self.escala_reducao = 1.0   # fator original -> reduzido
        self._calcular_fundo(caminho_video)

    @property
    def tem_fundo(self) -> bool:
        """False se o vídeo é curto/ilegível; então só o método por cor funciona."""
        return self.fundo_mediano is not None

    # ==================================================================
    # PREPARAÇÃO DO FUNDO
    # ==================================================================

    def _reduzir(self, frame):
        """Reduz o frame pela escala de detecção (mais rápido de processar)."""
        if self.escala_reducao == 1.0:
            return frame
        return cv2.resize(frame, None, fx=self.escala_reducao, fy=self.escala_reducao,
                          interpolation=cv2.INTER_AREA)

    def _calcular_fundo(self, caminho_video):
        """
        Calcula o fundo: mediana de vários frames espalhados pelo vídeo.
        Como o objeto passa por cada posição só por um instante, ele "some"
        da mediana e sobra a cena vazia.
        """
        # Leitura SEPARADA do vídeo, para não mexer na posição da leitura principal.
        cap = cv2.VideoCapture(caminho_video)
        try:
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            largura = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            if total < 10 or largura <= 0:
                return
            self.escala_reducao = min(1.0, config.DETECCAO_LARGURA_MAX / largura)

            amostras = []
            for i in np.linspace(0, total - 1, config.DETECCAO_AMOSTRAS_FUNDO).astype(int):
                cap.set(cv2.CAP_PROP_POS_FRAMES, int(i))
                ok, frame = cap.read()
                if ok:
                    amostras.append(self._reduzir(frame))
            if len(amostras) >= 5:
                self.fundo_mediano = np.median(np.stack(amostras), axis=0).astype(np.uint8)
        finally:
            cap.release()

    # ==================================================================
    # MÁSCARA DE MOVIMENTO E CANDIDATOS
    # ==================================================================

    def _mascara_movimento(self, frame):
        """
        Máscara (tamanho reduzido) das regiões que diferem do fundo.
        Retorna None se nada difere o bastante.
        """
        reduzido = self._reduzir(frame)
        if reduzido.shape != self.fundo_mediano.shape:
            return None

        # diferença com o fundo, no canal onde ela é maior, levemente suavizada
        diferenca = cv2.absdiff(reduzido, self.fundo_mediano).max(axis=2)
        diferenca = cv2.GaussianBlur(diferenca, (5, 5), 0)
        if diferenca.max() < config.DETECCAO_DIFERENCA_MIN:
            return None

        # limiar automático (Otsu), nunca abaixo do mínimo configurado
        otsu, _ = cv2.threshold(diferenca, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        limiar = max(config.DETECCAO_DIFERENCA_MIN, otsu)
        mascara = (diferenca > limiar).astype(np.uint8) * 255

        # abertura remove pontinhos de ruído; fechamento tapa "furos", como
        # o brilho de uma esfera
        mascara = cv2.morphologyEx(mascara, cv2.MORPH_OPEN, _elemento_estruturante(cv2.MORPH_ELLIPSE, (3, 3)))
        mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, _elemento_estruturante(cv2.MORPH_ELLIPSE, (9, 9)))

        # preenche o interior de cada região encontrada
        contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        mascara_preenchida = np.zeros_like(mascara)
        cv2.drawContours(mascara_preenchida, contornos, -1, 255, thickness=cv2.FILLED)
        return mascara_preenchida

    def _candidatos(self, mascara):
        """
        Regiões da máscara com tamanho plausível para o objeto.
        Retorna lista de (contorno, area, circularidade); circularidade = 1 é um círculo perfeito.
        """
        area_total = mascara.shape[0] * mascara.shape[1]
        contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        saida = []
        for c in contornos:
            area = cv2.contourArea(c)
            perimetro = cv2.arcLength(c, True)
            if perimetro == 0:
                continue
            if not (config.DETECCAO_AREA_MIN * area_total <= area <= config.DETECCAO_AREA_MAX * area_total):
                continue  # pequeno demais (ruído) ou grande demais (não é o objeto)
            saida.append((c, area, 4 * np.pi * area / perimetro ** 2))
        return saida

    def _caixa_do_contorno_original(self, contorno):
        """Caixa (x, y, largura, altura) do contorno, convertida para pixels originais."""
        x, y, w, h = cv2.boundingRect(contorno)
        return tuple(v / self.escala_reducao for v in (x, y, w, h))

    # ==================================================================
    # DETECÇÃO: INTERFACE PÚBLICA
    # ==================================================================

    def detectar_automatico(self, frame):
        """Procura o objeto sozinho (por movimento). Retorna a caixa ou None."""
        if not self.tem_fundo:
            return None
        mascara = self._mascara_movimento(frame)
        if mascara is None:
            return None
        candidatos = self._candidatos(mascara)
        if not candidatos:
            return None
        # prefere formas redondas e de bom tamanho
        contorno, _, _ = max(candidatos, key=lambda t: (t[2] ** 2) * np.sqrt(t[1]))
        return self._caixa_do_contorno_original(contorno)

    def detectar_no_ponto(self, frame, x, y):
        """
        Ajusta a caixa ao objeto que está sob o clique.

        Parâmetros: (x, y) em pixels do vídeo original.
        Tenta, nesta ordem: movimento, cor, caixa padrão.
        Retorna (caixa, metodo), com metodo em {"movimento", "cor", "padrao"}.
        """
        caixa = self._por_movimento(frame, x, y)
        if caixa is not None:
            return caixa, "movimento"
        caixa = self._por_cor(frame, x, y)
        if caixa is not None:
            return caixa, "cor"
        return self._caixa_padrao(frame, x, y), "padrao"

    # ==================================================================
    # MÉTODOS DE AJUSTE AO CLIQUE
    # ==================================================================

    def _por_movimento(self, frame, x, y):
        """Escolhe, entre as regiões em movimento, a que está sob (ou mais perto de) o clique."""
        if not self.tem_fundo:
            return None
        mascara = self._mascara_movimento(frame)
        if mascara is None:
            return None
        ponto = (float(x * self.escala_reducao), float(y * self.escala_reducao))
        tolerancia = max(6.0, 0.03 * mascara.shape[1])  # aceita clique um pouco fora da borda
        melhor_contorno, melhor_distancia = None, -tolerancia
        for contorno, _, _ in self._candidatos(mascara):
            distancia = cv2.pointPolygonTest(contorno, ponto, True)  # positivo = dentro
            if distancia >= melhor_distancia:
                melhor_contorno, melhor_distancia = contorno, distancia
        return self._caixa_do_contorno_original(melhor_contorno) if melhor_contorno is not None else None

    def _por_cor(self, frame, x, y):
        """
        Expande a partir do clique todos os pixels de cor parecida (flood fill)
        e devolve a caixa dessa região. Retorna None se o resultado não for confiável.
        """
        altura, largura = frame.shape[:2]

        # recorte quadrado em volta do clique, para limitar a busca
        meia_janela = int(config.CLIQUE_JANELA * min(altura, largura))
        x0, x1 = max(0, int(x) - meia_janela), min(largura, int(x) + meia_janela)
        y0, y1 = max(0, int(y) - meia_janela), min(altura, int(y) + meia_janela)
        recorte = cv2.GaussianBlur(frame[y0:y1, x0:x1], (5, 5), 0)
        altura_recorte, largura_recorte = recorte.shape[:2]
        semente = (int(x) - x0, int(y) - y0)  # o clique, em coordenadas do recorte
        if not (0 <= semente[0] < largura_recorte and 0 <= semente[1] < altura_recorte):
            return None

        # flood fill gravando só a máscara (a imagem não é alterada)
        mascara = np.zeros((altura_recorte + 2, largura_recorte + 2), np.uint8)
        tolerancia_cor = (config.CLIQUE_TOLERANCIA_COR,) * 3
        flags = 4 | cv2.FLOODFILL_MASK_ONLY | cv2.FLOODFILL_FIXED_RANGE | (255 << 8)
        cv2.floodFill(recorte, mascara, semente, (0, 0, 0), tolerancia_cor, tolerancia_cor, flags)
        regiao = mascara[1:-1, 1:-1]
        regiao = cv2.morphologyEx(regiao, cv2.MORPH_CLOSE, _elemento_estruturante(cv2.MORPH_ELLIPSE, (5, 5)))

        pontos = cv2.findNonZero(regiao)
        if pontos is None:
            return None
        bx, by, bw, bh = cv2.boundingRect(pontos)

        # Se a região encosta na borda do recorte, ela "vazou" para o fundo.
        # Se for minúscula, pegou só um detalhe do objeto. Nos dois casos, desiste.
        encostou_na_borda = (bx == 0 or by == 0
                             or bx + bw >= largura_recorte or by + bh >= altura_recorte)
        if encostou_na_borda or min(bw, bh) < config.ROI_MINIMA_PX:
            return None
        return (bx + x0, by + y0, bw, bh)

    @staticmethod
    def _caixa_padrao(frame, x, y):
        """Último recurso: quadrado de tamanho fixo centrado no clique."""
        altura, largura = frame.shape[:2]
        lado = max(config.ROI_MINIMA_PX * 2, config.CLIQUE_LADO_PADRAO * min(altura, largura))
        x0 = min(max(0.0, x - lado / 2), largura - lado)
        y0 = min(max(0.0, y - lado / 2), altura - lado)
        return (x0, y0, lado, lado)