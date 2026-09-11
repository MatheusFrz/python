# -*- coding: utf-8 -*-
"""
Parâmetros do experimento.

Mantém as constantes físicas e de exibição isoladas do resto da lógica,
para que ajustar o experimento não exija mexer em código de rastreamento
ou de exportação.
"""

RAIO_M = 0.0212      # raio real do objeto rastreado, em metros
TEMPO_S = 1 / 120     # intervalo entre frames em segundos (1 / fps do vídeo)
MARGEM_TELA = 0.85    # fração da tela usada para a janela de exibição

# fator de lentidão apenas da EXIBIÇÃO na tela — não afeta o tempo real
# gravado no CSV (que continua baseado em TEMPO_S). 1.0 = tempo real,
# 2.0 = tela roda duas vezes mais devagar, 0.5 = duas vezes mais rápido.
FATOR_LENTIDAO_EXIBICAO = 1.0
