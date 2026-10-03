# -*- coding: utf-8 -*-
"""
config.py - todos os parâmetros do programa, num só lugar.

Quem usa: main.py, interface.py, deteccao.py.

Regra do projeto: nenhum número "solto" no código. Se um valor pode ser
ajustado (experimento, desempenho, sensibilidade), ele vira constante aqui.
Assim dá para calibrar o programa sem mexer na lógica.

Seções:
    1. Experimento   - valores físicos
    2. Exibição      - velocidade do vídeo na tela
    3. Interface     - tamanhos e desempenho da janela
    4. Marcação      - tamanho mínimo da região marcada e clique
    5. Detecção      - ajustes da detecção automática do objeto
"""

# ======================================================================
# 1. EXPERIMENTO
# ======================================================================
# Valores INICIAIS dos campos "Raio do objeto" e "FPS do video" da janela.
# Cada medida pode usar valores diferentes: basta mudar os campos na tela.

RAIO_OBJETO_M = 0.0212         # raio real do objeto rastreado, em metros
INTERVALO_FRAME_S = 1 / 120    # tempo entre dois frames, em segundos (= 1 / fps do vídeo)

# ======================================================================
# 2. EXIBIÇÃO
# ======================================================================

# (Sem uso na versão atual: pertencia à janela do OpenCV. Pode ser removida.)
MARGEM_TELA = 0.85

# Lentidão da EXIBIÇÃO apenas. Não altera o tempo gravado no CSV, que vem
# sempre do fps do vídeo.
#   1.0 = tempo real | 2.0 = duas vezes mais devagar | 0.5 = duas vezes mais rápido
# (Só tem efeito se o computador for mais rápido que o tempo real.)
FATOR_LENTIDAO_EXIBICAO = 1.0

# ======================================================================
# 3. INTERFACE (DearPyGui)
# ======================================================================

# Tamanho do painel de vídeo, em pixels. Painel menor = tela mais leve de
# desenhar, que é o que mais pesa em computadores simples.
#   Referência: 640x360 (leve) | 800x450 (médio) | 960x540 (pesado)
PAINEL_VIDEO_LARGURA = 640
PAINEL_VIDEO_ALTURA = 360

# Largura da coluna com os três gráficos, em pixels.
LARGURA_GRAFICOS = 440

# Tempo máximo (s) que cada ciclo da janela pode gastar rastreando frames.
# É o que impede a janela de travar quando o computador não acompanha o
# tempo real: o vídeo passa mais devagar, mas a tela continua respondendo.
# Sugestão: cerca de 70% de um ciclo de tela (1/60 s = 0,0167 s).
ORCAMENTO_CICLO_S = 0.012

# Intervalo mínimo entre redesenhos dos gráficos, em segundos.
# 0.1 = 10 atualizações por segundo (60 por segundo seria desperdício).
INTERVALO_GRAFICOS_S = 0.1

# ======================================================================
# 4. MARCAÇÃO DO OBJETO
# ======================================================================

# Menor região marcada aceita, em pixels do vídeo ORIGINAL. Marcações
# menores são descartadas (evita um clique sem querer virar rastreamento).
ROI_MINIMA_PX = 8

# Arrasto do mouse menor que isto (em pixels do painel) conta como CLIQUE.
LIMIAR_CLIQUE_PAINEL_PX = 5

# ======================================================================
# 5. DETECÇÃO AUTOMÁTICA (deteccao.py)
# ======================================================================

# -- Por movimento: compara o frame com um "fundo sem o objeto" --
DETECCAO_AMOSTRAS_FUNDO = 25    # quantos frames do vídeo entram no fundo (mediana)
DETECCAO_LARGURA_MAX = 480      # a detecção usa uma versão reduzida do frame (mais rápida)
DETECCAO_DIFERENCA_MIN = 20     # diferença mínima (0-255) para considerar "algo novo"
DETECCAO_AREA_MIN = 0.0002      # tamanho plausível do objeto, como fração da imagem
DETECCAO_AREA_MAX = 0.20

# -- Por clique: expande a região de cor parecida em volta do clique --
CLIQUE_TOLERANCIA_COR = 18      # quão parecida a cor precisa ser (0-255)
CLIQUE_JANELA = 0.25            # região de busca em volta do clique (fração do menor lado)
CLIQUE_LADO_PADRAO = 0.06       # caixa de último recurso (fração do menor lado do vídeo)