# -*- coding: utf-8 -*-
"""
interface.py - a janela (DearPyGui): botões, campos, vídeo e gráficos.

Papel:
    Só DESENHA e LÊ CAMPOS. Não rastreia, não grava, não decide nada. Quando
    um botão é clicado, avisa o main.py chamando uma função que ele forneceu
    (os parâmetros "on_..." de criar_janela). Assim a lógica fica toda no
    main.py e este arquivo pode mudar de visual sem afetar o resto.

Layout da janela:
    +----------------------------------------------------+
    | [Selecionar] [Iniciar] [Parar] [Remarcar]          |  botões
    | FPS: [____]   Raio (m): [____]                     |  campos
    +---------------------------+------------------------+
    |                           |  gráfico X(t)          |
    |   painel de vídeo         |  gráfico Y(t)          |
    |   texto de status         |  gráfico Y(X)          |
    +---------------------------+------------------------+

Como o vídeo chega na tela: cada frame vira uma textura (imagem na placa de
vídeo) que o DearPyGui exibe. Os buffers abaixo são reutilizados a cada frame
para não alocar memória 60 vezes por segundo.

Estrutura do arquivo:
    1. Constantes e estado do módulo
    2. Construção da janela      (criar_janela)
    3. Painel de vídeo           (atualizar_video, mouse)
    4. Gráficos
    5. Textos e controles        (status, campos, botões)
    6. Diálogo de arquivo e encerramento

Usado por: main.py.
"""

import cv2
import numpy as np
import dearpygui.dearpygui as dpg

import config
from video_utils import ajustar_ao_painel

# ======================================================================
# 1. CONSTANTES E ESTADO DO MÓDULO
# ======================================================================

# Altura de cada gráfico: divide a altura do painel de vídeo entre os três
# (descontando o espaçamento), com um mínimo para continuarem legíveis.
_ALTURA_GRAFICO = max(130, (config.PAINEL_VIDEO_ALTURA - 16) // 3)
_ALTURA_CONTEUDO = max(config.PAINEL_VIDEO_ALTURA + 60, 3 * _ALTURA_GRAFICO + 16)
_ALTURA_CONTROLES = 120   # espaço reservado para botões e campos, em pixels

# Buffers reutilizados a cada frame (criados em criar_janela):
_buffer_rgba_u8 = None      # frame em RGBA, inteiros 0-255
_buffer_rgba_float = None   # o mesmo em decimais 0-1, formato que a textura exige

# Tags (nomes internos) das séries dos gráficos. Cada série tem também dois
# eixos, com tags "<série>_eixo_x" e "<série>_eixo_y".
_TAGS_SERIES = ("serie_x", "serie_y", "serie_traj")

_COR_MARCACAO = (0, 255, 255)   # cor do retângulo de marcação (BGR = amarelo)

# Filtro do diálogo de arquivo. As maiúsculas são listadas porque o filtro
# diferencia maiúsculas de minúsculas.
_EXTENSOES_VIDEO = "Videos (*.mp4 *.avi *.mov *.mkv){.mp4,.avi,.mov,.mkv,.MP4,.AVI,.MOV,.MKV}"


# ======================================================================
# 2. CONSTRUÇÃO DA JANELA
# ======================================================================

def _criar_grafico(titulo, rotulo_x, rotulo_y, tag_serie, eixos_iguais=False):
    """
    Cria um gráfico com uma série de linha, vazia a princípio.

    Parâmetros:
        tag_serie: nome interno da série (usado depois para atualizá-la).
        eixos_iguais: True mantém a mesma escala em X e Y, de modo que 1 m
            ocupa o mesmo comprimento nos dois eixos (sem distorcer a trajetória).
    """
    with dpg.plot(
        label=titulo,
        width=config.LARGURA_GRAFICOS,
        height=_ALTURA_GRAFICO,
        equal_aspects=eixos_iguais,
    ):
        dpg.add_plot_axis(dpg.mvXAxis, label=rotulo_x, tag=f"{tag_serie}_eixo_x")
        with dpg.plot_axis(dpg.mvYAxis, label=rotulo_y, tag=f"{tag_serie}_eixo_y"):
            dpg.add_line_series([], [], tag=tag_serie)


def criar_janela(on_selecionar, on_arquivo, on_iniciar, on_parar, on_remarcar):
    """
    Monta a janela inteira e a exibe.

    Os parâmetros "on_..." são funções do main.py chamadas pelos botões. A
    interface não sabe o que elas fazem, só avisa que houve o clique:
        on_selecionar -> botão "Selecionar video"
        on_arquivo    -> diálogo do DearPyGui concluído (recebe o caminho)
        on_iniciar    -> botão "Iniciar rastreamento"
        on_parar      -> botão "Parar"
        on_remarcar   -> botão "Remarcar objeto"
    """
    global _buffer_rgba_u8, _buffer_rgba_float
    dpg.create_context()

    forma = (config.PAINEL_VIDEO_ALTURA, config.PAINEL_VIDEO_LARGURA, 4)
    _buffer_rgba_u8 = np.zeros(forma, dtype=np.uint8)
    _buffer_rgba_float = np.zeros(forma, dtype=np.float32)

    # -- textura que recebe cada frame do vídeo (RGBA, decimais 0-1) --
    with dpg.texture_registry():
        dpg.add_raw_texture(
            config.PAINEL_VIDEO_LARGURA,
            config.PAINEL_VIDEO_ALTURA,
            _buffer_rgba_float.ravel(),
            tag="tex_video",
            format=dpg.mvFormat_Float_rgba,
        )

    # -- diálogo de arquivo do próprio DearPyGui (plano B, se não houver tkinter) --
    def _arquivo_escolhido(sender, app_data):
        caminho = app_data.get("file_path_name", "")
        if not caminho and app_data.get("selections"):
            caminho = next(iter(app_data["selections"].values()))
        if caminho:
            on_arquivo(caminho)

    with dpg.file_dialog(
        directory_selector=False,
        show=False,
        modal=True,
        callback=_arquivo_escolhido,
        tag="dialogo_arquivo",
        width=700,
        height=420,
    ):
        dpg.add_file_extension(_EXTENSOES_VIDEO)
        dpg.add_file_extension(".*")

    # -- conteúdo da janela principal --
    with dpg.window(tag="janela_principal"):
        # linha 1: botões
        with dpg.group(horizontal=True):
            dpg.add_button(label="Selecionar video", tag="btn_selecionar", width=150,
                           callback=on_selecionar)
            dpg.add_button(label="Iniciar rastreamento", tag="btn_iniciar", width=170, callback=on_iniciar)
            dpg.add_button(label="Parar", tag="btn_parar", width=80, callback=on_parar)
            dpg.add_button(label="Remarcar objeto", tag="btn_remarcar", width=140, callback=on_remarcar)

        # linha 2: campos de FPS e raio (valores iniciais vêm do config.py)
        with dpg.group(horizontal=True):
            dpg.add_text("FPS do video:")
            dpg.add_input_float(tag="campo_fps", width=110, step=0, format="%.2f",
                                default_value=round(1 / config.INTERVALO_FRAME_S, 2))
            dpg.add_text("   Raio do objeto (m):")
            dpg.add_input_float(tag="campo_raio", width=110, step=0, format="%.4f",
                                default_value=config.RAIO_OBJETO_M)
            dpg.add_text("", tag="info_fps")   # mostra o FPS que o arquivo informa
        dpg.add_separator()

        # área principal: vídeo + status à esquerda, gráficos à direita
        with dpg.group(horizontal=True):
            with dpg.group():
                dpg.add_image("tex_video", tag="img_video")
                dpg.add_text("", tag="status", wrap=config.PAINEL_VIDEO_LARGURA)
            with dpg.group():
                _criar_grafico("Posição X", "Tempo (s)", "X (m)", "serie_x")
                _criar_grafico("Posição Y", "Tempo (s)", "Y (m)", "serie_y")
                _criar_grafico("Trajetória", "X (m)", "Y (m)", "serie_traj", eixos_iguais=True)

    dpg.create_viewport(
        title="Rastreamento de Objeto",
        width=config.PAINEL_VIDEO_LARGURA + config.LARGURA_GRAFICOS + 60,
        height=_ALTURA_CONTEUDO + _ALTURA_CONTROLES + 70,
    )
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("janela_principal", True)


# ======================================================================
# 3. PAINEL DE VÍDEO
# ======================================================================

def _enviar_para_textura(canvas):
    """Converte a imagem do painel (BGR) para RGBA decimal e a envia à textura."""
    cv2.cvtColor(canvas, cv2.COLOR_BGR2RGBA, dst=_buffer_rgba_u8)
    np.multiply(_buffer_rgba_u8, np.float32(1 / 255), out=_buffer_rgba_float, dtype=np.float32)
    dpg.set_value("tex_video", _buffer_rgba_float.ravel())


def atualizar_video(frame, roi_painel=None):
    """
    Exibe o frame no painel, sem distorção.

    Parâmetros:
        frame: imagem BGR em resolução original.
        roi_painel: opcional, (x1, y1, x2, y2) em pixels do PAINEL. Se dado,
            desenha o retângulo de marcação por cima.

    Retorna (escala, offset), necessários para converter cliques do painel em
    pixels do vídeo (ver video_utils.painel_para_original).
    """
    canvas, escala, offset = ajustar_ao_painel(
        frame, config.PAINEL_VIDEO_LARGURA, config.PAINEL_VIDEO_ALTURA
    )
    if roi_painel is not None:
        x1, y1, x2, y2 = (int(round(v)) for v in roi_painel)
        cv2.rectangle(canvas, (x1, y1), (x2, y2), _COR_MARCACAO, 2)
    _enviar_para_textura(canvas)
    return escala, offset


def mostrar_placeholder(texto: str):
    """Painel preto com uma mensagem centralizada (sem acentos: a fonte do OpenCV não os tem)."""
    canvas = np.zeros((config.PAINEL_VIDEO_ALTURA, config.PAINEL_VIDEO_LARGURA, 3), dtype=np.uint8)
    (w, h), _ = cv2.getTextSize(texto, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 1)
    cv2.putText(canvas, texto, ((config.PAINEL_VIDEO_LARGURA - w) // 2,
                                (config.PAINEL_VIDEO_ALTURA + h) // 2),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1, cv2.LINE_AA)
    _enviar_para_textura(canvas)


def posicao_mouse_no_painel():
    """
    Posição do mouse relativa ao canto superior esquerdo do painel de vídeo.
    Retorna (x, y, sobre_o_painel); o terceiro valor diz se o mouse está sobre ele.
    """
    mx, my = dpg.get_mouse_pos(local=False)
    rx, ry = dpg.get_item_rect_min("img_video")
    return mx - rx, my - ry, dpg.is_item_hovered("img_video")


def mouse_esquerdo_pressionado() -> bool:
    return dpg.is_mouse_button_down(dpg.mvMouseButton_Left)


# ======================================================================
# 4. GRÁFICOS
# ======================================================================

def atualizar_graficos(tempos, xs, ys):
    """Redesenha as três séries com todos os pontos acumulados até agora."""
    dpg.set_value("serie_x", [tempos, xs])
    dpg.set_value("serie_y", [tempos, ys])
    dpg.set_value("serie_traj", [xs, ys])
    for tag in _TAGS_SERIES:  # reajusta os eixos para acompanhar os dados que crescem
        dpg.fit_axis_data(f"{tag}_eixo_x")
        dpg.fit_axis_data(f"{tag}_eixo_y")


def limpar_graficos():
    for tag in _TAGS_SERIES:
        dpg.set_value(tag, [[], []])


# ======================================================================
# 5. TEXTOS E CONTROLES
# ======================================================================

def mostrar_status(texto: str):
    """Texto de orientação abaixo do vídeo."""
    dpg.set_value("status", texto)


def mostrar_fps_detectado(fps):
    """Mostra ao lado do campo de FPS o valor que o arquivo informa (para conferência)."""
    texto = f"   (detectado no arquivo: {fps:.2f})" if fps and fps > 0 else ""
    dpg.set_value("info_fps", texto)


def ler_campos_do_experimento():
    """Lê os campos da janela. Retorna (fps, raio_em_metros)."""
    return dpg.get_value("campo_fps"), dpg.get_value("campo_raio")


def habilitar_botoes(selecionar: bool, iniciar: bool, parar: bool, remarcar: bool):
    """
    Liga ou desliga cada botão conforme o estado do programa.
    Os campos de FPS e raio só podem ser editados quando não há rastreamento em curso.
    """
    dpg.configure_item("btn_selecionar", enabled=selecionar)
    dpg.configure_item("btn_iniciar", enabled=iniciar)
    dpg.configure_item("btn_parar", enabled=parar)
    dpg.configure_item("btn_remarcar", enabled=remarcar)
    dpg.configure_item("campo_fps", enabled=selecionar or remarcar)
    dpg.configure_item("campo_raio", enabled=selecionar or remarcar)


# ======================================================================
# 6. DIÁLOGO DE ARQUIVO E ENCERRAMENTO
# ======================================================================

def mostrar_dialogo_dpg():
    """Abre o diálogo de arquivo do DearPyGui (plano B, se o nativo não existir)."""
    dpg.show_item("dialogo_arquivo")


def encerrar():
    """Libera os recursos da janela."""
    dpg.destroy_context()