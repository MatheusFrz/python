# -*- coding: utf-8 -*-
"""
main.py - ponto de entrada e "cérebro" do programa.

Papel:
    Liga as peças e decide O QUE fazer a cada momento. As outras peças só
    executam:
        interface.py       desenha a janela e lê campos (não decide nada)
        deteccao.py        acha o objeto no primeiro frame
        rastreador.py      segue o objeto frame a frame (KCF)
        conversao.py       converte pixels em metros
        exportador_csv.py  grava Tempo,X,Y
        selecao_video.py   diálogo nativo para escolher o arquivo
        video_utils.py     ajuste do frame ao painel e conversão de coordenadas
        config.py          constantes

Tudo acontece numa única janela, controlada por uma MÁQUINA DE ESTADOS. O
programa está sempre em exatamente um destes estados, e o loop principal
decide o que fazer olhando só para ele:

    ESTADO_SEM_VIDEO   -- escolhe um vídeo ---------------> ESTADO_MARCANDO
    ESTADO_MARCANDO    -- "Iniciar rastreamento" ----------> ESTADO_RASTREANDO
    ESTADO_RASTREANDO  -- fim do vídeo ou "Parar" ---------> ESTADO_FIM
    ESTADO_FIM         -- "Remarcar" ou novo vídeo --------> ESTADO_MARCANDO

Convenções usadas nos nomes:
    "original"  pixels do vídeo em resolução real
    "painel"    pixels da área de vídeo na janela (menor, com barras pretas)
    "ROI"       região de interesse: a caixa marcada sobre o objeto
    "bbox"      caixa (x, y, largura, altura)

Uso:
    python main.py                   abre a janela; o vídeo é escolhido por botão
    python main.py "meu video.mp4"   já abre esse vídeo
"""

import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import dearpygui.dearpygui as dpg

import config
import interface
from deteccao import DetectorObjeto
from selecao_video import escolher_video_nativo
from video_utils import dimensoes_video, painel_para_original, original_para_painel
from rastreador import RastreadorKCF, desenhar_bbox
from conversao import bbox_para_metros
from exportador_csv import ExportadorCSV

# Os quatro estados da máquina de estados (números 0 a 3; só os nomes importam)
ESTADO_SEM_VIDEO, ESTADO_MARCANDO, ESTADO_RASTREANDO, ESTADO_FIM = range(4)


class Aplicacao:
    # ==================================================================
    # ESTADO DO PROGRAMA
    # ==================================================================

    def __init__(self):
        self.estado = ESTADO_SEM_VIDEO

        # -- vídeo carregado --
        self.cap = None                  # leitor do vídeo (cv2.VideoCapture)
        self.caminho_video = None
        self.detector = None             # DetectorObjeto do vídeo atual
        self.primeiro_frame = None       # usado para marcar o objeto
        self.largura_video = 0.0         # em pixels originais
        self.altura_video = 0.0
        self.escala_painel = 1.0         # fator original -> painel
        self.offset_painel = (0, 0)      # barras pretas (x, y) dentro do painel

        # -- marcação do objeto (coordenadas do PAINEL) --
        self.roi_painel = None           # (x1, y1, x2, y2) já finalizada; None = sem marcação
        self._arrastando = False
        self._ponto_inicial_arrasto = None
        self._mouse_estava_pressionado = False   # estado do botão no ciclo anterior

        # -- diálogo de arquivo (roda em outra thread, para a janela não congelar) --
        self._executor_dialogo = ThreadPoolExecutor(max_workers=1)
        self._escolha_pendente = None            # resultado futuro da escolha; None = nenhum diálogo aberto
        self._dialogo_nativo_indisponivel = False   # sem tkinter: usa o diálogo do DearPyGui

        # -- rastreamento --
        self.rastreador = None
        self.exportador = None
        self.caminho_csv = None
        self.intervalo_frame_s = config.INTERVALO_FRAME_S    # 1 / fps; define o tempo gravado
        self.raio_objeto_m = config.RAIO_OBJETO_M            # escala da medição (ver conversao.py)
        self.intervalo_exibicao_s = config.INTERVALO_FRAME_S * config.FATOR_LENTIDAO_EXIBICAO
        self.tempos, self.xs, self.ys = [], [], []           # dados acumulados, para os gráficos
        self.tempo_acumulado = 0.0
        self.instante_proximo_frame = 0.0                    # relógio: quando exibir o próximo frame
        self.instante_ultimo_desenho_graficos = 0.0

    # ==================================================================
    # CICLO DE VIDA
    # ==================================================================

    def executar(self):
        """Cria a janela e roda o loop principal até ela ser fechada."""
        interface.criar_janela(
            on_selecionar=self.selecionar_video,
            on_arquivo=self.carregar_video,
            on_iniciar=self.iniciar_rastreamento,
            on_parar=self.parar_rastreamento,
            on_remarcar=self.remarcar,
        )
        interface.mostrar_placeholder("Clique em 'Selecionar video'")
        interface.mostrar_status("Escolha um video para comecar.")
        self._atualizar_botoes()

        # vídeo passado na linha de comando: já abre direto
        if len(sys.argv) > 1 and Path(sys.argv[1]).is_file():
            self.carregar_video(sys.argv[1])

        # Cada volta deste loop é um ciclo de desenho da janela (cerca de 60 por segundo).
        while dpg.is_dearpygui_running():
            self._verificar_dialogo_concluido()
            if self.estado == ESTADO_MARCANDO:
                self._processar_mouse_marcacao()
            if self.estado == ESTADO_RASTREANDO:
                self._avancar_rastreamento()
            else:
                time.sleep(0.015)  # nada a processar: não gasta CPU à toa
            dpg.render_dearpygui_frame()  # desenha a janela (obrigatório a cada ciclo)

    def encerrar(self):
        """Libera tudo, mesmo se a janela for fechada no meio do rastreamento."""
        self._executor_dialogo.shutdown(wait=False, cancel_futures=True)
        self._fechar_csv()
        self._liberar_video()
        interface.encerrar()

    # ==================================================================
    # ESCOLHA DO VÍDEO
    # ==================================================================

    def selecionar_video(self):
        """Botão 'Selecionar video': abre o diálogo nativo sem travar a janela."""
        if self._escolha_pendente is not None or self.estado == ESTADO_RASTREANDO:
            return
        if self._dialogo_nativo_indisponivel:
            interface.mostrar_dialogo_dpg()
            return
        self._escolha_pendente = self._executor_dialogo.submit(escolher_video_nativo)
        interface.mostrar_status("Escolha o video na janela de selecao que abriu...")
        self._atualizar_botoes()

    def _verificar_dialogo_concluido(self):
        """Chamada a cada ciclo: se o diálogo terminou, trata o resultado."""
        if self._escolha_pendente is None or not self._escolha_pendente.done():
            return
        try:
            caminho = self._escolha_pendente.result()
        except Exception:
            caminho = None
        self._escolha_pendente = None

        if caminho is None:               # sem diálogo nativo: usa o do DearPyGui
            self._dialogo_nativo_indisponivel = True
            self._atualizar_botoes()
            interface.mostrar_dialogo_dpg()
        elif caminho:                     # escolheu um arquivo
            self.carregar_video(caminho)
        else:                             # cancelou: volta como estava
            self._atualizar_botoes()
            interface.mostrar_status("Nenhum video escolhido.")

    def carregar_video(self, caminho):
        """Abre o vídeo, prepara a detecção e passa para a marcação do objeto."""
        if self.estado == ESTADO_RASTREANDO:
            return
        cap = cv2.VideoCapture(caminho)
        ret, frame = cap.read() if cap.isOpened() else (False, None)
        if not ret:
            cap.release()
            interface.mostrar_status("Nao foi possivel abrir esse arquivo como video.")
            return

        self._liberar_video()
        self.cap = cap
        self.caminho_video = caminho
        self.largura_video, self.altura_video = dimensoes_video(cap)
        self.detector = DetectorObjeto(caminho)  # prepara o "fundo" para a detecção
        interface.mostrar_fps_detectado(cap.get(cv2.CAP_PROP_FPS))
        self._preparar_marcacao(frame)

    # ==================================================================
    # BOTÕES DE AÇÃO
    # ==================================================================

    def remarcar(self):
        """Volta ao primeiro frame do mesmo vídeo e detecta o objeto de novo."""
        if self.cap is None or self.estado == ESTADO_RASTREANDO:
            return
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ret, frame = self.cap.read()
        if not ret:
            interface.mostrar_status("Nao foi possivel voltar ao inicio do video.")
            return
        self._preparar_marcacao(frame)

    def iniciar_rastreamento(self):
        """Valida a marcação e os campos, abre o CSV e entra em ESTADO_RASTREANDO."""
        if self.estado != ESTADO_MARCANDO or self.roi_painel is None:
            return

        # -- validações --
        fps, raio = interface.ler_campos_do_experimento()
        if fps <= 0 or raio <= 0:
            interface.mostrar_status("FPS e raio precisam ser maiores que zero.")
            return

        bbox = self._roi_em_pixels_do_video()
        if min(bbox[2], bbox[3]) < config.ROI_MINIMA_PX:
            interface.mostrar_status("Marcacao muito pequena. Clique no objeto ou arraste de novo.")
            return

        # -- arquivo de saída: fica na mesma pasta do vídeo --
        pasta = Path(self.caminho_video).parent
        self.caminho_csv = str(pasta / f"{Path(self.caminho_video).stem} - posicoes.csv")
        try:
            self.exportador = ExportadorCSV(self.caminho_csv)
        except OSError:
            self.exportador = None
            interface.mostrar_status("Nao foi possivel criar o CSV. Ele esta aberto em outro programa?")
            return

        # -- parâmetros desta medida (lidos dos campos da janela) --
        self.intervalo_frame_s = 1 / fps
        self.raio_objeto_m = raio
        self.intervalo_exibicao_s = self.intervalo_frame_s * config.FATOR_LENTIDAO_EXIBICAO
        self.rastreador = RastreadorKCF(self.primeiro_frame, bbox)

        # -- ponto inicial: o objeto no primeiro frame, em t = 0 --
        self.tempos, self.xs, self.ys = [], [], []
        self._registrar_ponto(0.0, self.rastreador.bbox_inicial)
        interface.limpar_graficos()
        interface.atualizar_graficos(self.tempos, self.xs, self.ys)

        self.tempo_acumulado = 0.0
        self.instante_proximo_frame = time.perf_counter()
        self.instante_ultimo_desenho_graficos = 0.0
        self.estado = ESTADO_RASTREANDO
        self._atualizar_botoes()
        interface.mostrar_status("Rastreando...")

    def parar_rastreamento(self):
        """Botão 'Parar': encerra antes do fim do vídeo (o CSV fica salvo até aqui)."""
        if self.estado == ESTADO_RASTREANDO:
            self._finalizar_rastreamento("Parado")

    # ==================================================================
    # MARCAÇÃO DO OBJETO (ESTADO_MARCANDO)
    # ==================================================================

    def _preparar_marcacao(self, frame):
        """Entra em ESTADO_MARCANDO: mostra o primeiro frame e tenta detectar o objeto."""
        self.primeiro_frame = frame
        self.roi_painel = None
        self._arrastando = False
        self._mouse_estava_pressionado = False
        self._fechar_csv()
        self.tempos, self.xs, self.ys = [], [], []
        interface.limpar_graficos()
        self.escala_painel, self.offset_painel = interface.atualizar_video(frame)
        self.estado = ESTADO_MARCANDO

        # proposta inicial: o programa tenta achar o objeto sozinho
        caixa = self.detector.detectar_automatico(frame)
        if caixa is not None and self._definir_roi_pela_caixa_do_video(caixa):
            self._mostrar_status_roi("Objeto detectado automaticamente.")
        else:
            interface.mostrar_status(
                "Nao consegui achar o objeto sozinho. Clique nele ou arraste um retangulo ao redor."
            )
        self._atualizar_botoes()

    def _processar_mouse_marcacao(self):
        """
        Acompanha o mouse sobre o painel. Distingue duas ações:
            CLIQUE (arrasto curto): o programa ajusta a caixa ao objeto clicado
            ARRASTO: marcação manual de um retângulo
        """
        pressionado = interface.mouse_esquerdo_pressionado()
        x, y, sobre_painel = interface.posicao_mouse_no_painel()

        # 1) começou a pressionar sobre o painel: guarda o ponto inicial
        if pressionado and not self._mouse_estava_pressionado and sobre_painel:
            self._arrastando = True
            self._ponto_inicial_arrasto = self._limitar_a_area_do_video(x, y)

        # 2) segurando o botão: mostra o retângulo acompanhando o mouse
        if self._arrastando and pressionado:
            xf, yf = self._limitar_a_area_do_video(x, y)
            xi, yi = self._ponto_inicial_arrasto
            interface.atualizar_video(self.primeiro_frame, (xi, yi, xf, yf))

        # 3) soltou o botão: decide se foi clique ou arrasto
        if self._arrastando and not pressionado:
            self._arrastando = False
            xf, yf = self._limitar_a_area_do_video(x, y)
            xi, yi = self._ponto_inicial_arrasto
            deslocamento_px = max(abs(xf - xi), abs(yf - yi))

            if deslocamento_px < config.LIMIAR_CLIQUE_PAINEL_PX:
                self._marcar_por_clique(xf, yf)
            else:
                self._marcar_por_arrasto(xi, yi, xf, yf)
            self._atualizar_botoes()

        self._mouse_estava_pressionado = pressionado

    def _marcar_por_clique(self, x_painel, y_painel):
        """Ajusta a caixa ao objeto sob o clique (ver deteccao.detectar_no_ponto)."""
        ox, oy = painel_para_original(x_painel, y_painel, self.escala_painel, self.offset_painel)
        caixa, metodo = self.detector.detectar_no_ponto(self.primeiro_frame, ox, oy)
        self._definir_roi_pela_caixa_do_video(caixa)
        if metodo == "padrao":
            self._mostrar_status_roi("Nao consegui contornar o objeto; coloquei uma caixa padrao. "
                                     "Ajuste arrastando.")
        else:
            self._mostrar_status_roi("Retangulo ajustado ao objeto clicado.")

    def _marcar_por_arrasto(self, x1, y1, x2, y2):
        """Usa o retângulo desenhado à mão (descarta se for pequeno demais)."""
        self.roi_painel = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
        if min(self._roi_em_pixels_do_video()[2:]) < config.ROI_MINIMA_PX:
            self.roi_painel = None
            interface.atualizar_video(self.primeiro_frame)
            interface.mostrar_status("Marcacao muito pequena. Clique no objeto ou arraste de novo.")
            return
        interface.atualizar_video(self.primeiro_frame, self.roi_painel)
        self._mostrar_status_roi("Retangulo marcado a mao.")

    def _definir_roi_pela_caixa_do_video(self, caixa):
        """
        Mostra no painel uma caixa dada em pixels ORIGINAIS e a adota como ROI.
        Retorna False (sem alterar nada) se a caixa for pequena demais.
        """
        x, y, w, h = caixa
        if min(w, h) < config.ROI_MINIMA_PX:
            return False
        x1, y1 = original_para_painel(x, y, self.escala_painel, self.offset_painel)
        x2, y2 = original_para_painel(x + w, y + h, self.escala_painel, self.offset_painel)
        self.roi_painel = (x1, y1, x2, y2)
        interface.atualizar_video(self.primeiro_frame, self.roi_painel)
        return True

    def _mostrar_status_roi(self, prefixo):
        """Resume a marcação e deixa explícita a regra de escala usada nos cálculos."""
        _, _, w, h = self._roi_em_pixels_do_video()
        _, raio = interface.ler_campos_do_experimento()
        interface.mostrar_status(
            f"{prefixo} Caixa: {w:.0f} x {h:.0f} px.\n"
            f"Escala: a LARGURA da caixa sera tratada como {raio * 1000:.1f} mm "
            f"(valor do campo 'Raio').\n"
            "Se estiver certo, clique em 'Iniciar rastreamento'. "
            "Para corrigir, clique no objeto ou arraste um retangulo."
        )

    # -- conversões de coordenadas da marcação --

    def _limitar_a_area_do_video(self, x, y):
        """Mantém um ponto do painel dentro da área do vídeo (fora das barras pretas)."""
        x0, y0 = self.offset_painel
        largura = self.largura_video * self.escala_painel
        altura = self.altura_video * self.escala_painel
        return min(max(x, x0), x0 + largura), min(max(y, y0), y0 + altura)

    def _roi_em_pixels_do_video(self):
        """Converte a ROI do painel para (x, y, largura, altura) em pixels ORIGINAIS."""
        x1, y1, x2, y2 = self.roi_painel
        ox1, oy1 = painel_para_original(x1, y1, self.escala_painel, self.offset_painel)
        ox2, oy2 = painel_para_original(x2, y2, self.escala_painel, self.offset_painel)
        ox1, ox2 = max(0.0, ox1), min(self.largura_video, ox2)
        oy1, oy2 = max(0.0, oy1), min(self.altura_video, oy2)
        return ox1, oy1, ox2 - ox1, oy2 - oy1

    # ==================================================================
    # RASTREAMENTO (ESTADO_RASTREANDO)
    # ==================================================================

    def _registrar_ponto(self, tempo_s, bbox):
        """Converte a caixa em metros e guarda o ponto no CSV e nas listas dos gráficos."""
        x_m, y_m = bbox_para_metros(
            bbox,
            self.altura_video,
            self.rastreador.largura_roi,
            self.rastreador.altura_roi,
            self.raio_objeto_m,
        )
        self.exportador.registrar(tempo_s, x_m, y_m)
        self.tempos.append(tempo_s)
        self.xs.append(x_m)
        self.ys.append(y_m)

    def _avancar_rastreamento(self):
        """
        Executada a cada ciclo da janela durante o rastreamento.

        Ideia: o vídeo tem N frames por segundo, mas a janela só desenha ~60
        ciclos por segundo. Então cada ciclo processa os frames que "venceram"
        desde o último (ex.: vídeo de 120 fps => cerca de 2 frames por ciclo),
        mas NUNCA gasta mais que ORCAMENTO_CICLO_S rastreando. Assim a janela
        continua respondendo mesmo em computadores lentos (o vídeo apenas
        passa mais devagar, e nenhum frame é pulado).
        """
        inicio_ciclo = agora = time.perf_counter()
        ultimo_frame = None
        fim_do_video = False

        # -- processa os frames que já venceram --
        while agora >= self.instante_proximo_frame:
            ret, frame = self.cap.read()
            if not ret:
                fim_do_video = True
                break

            self.tempo_acumulado += self.intervalo_frame_s
            sucesso, bbox = self.rastreador.atualizar(frame)
            if sucesso:
                desenhar_bbox(frame, bbox)
                self._registrar_ponto(self.tempo_acumulado, bbox)

            ultimo_frame = frame
            self.instante_proximo_frame += self.intervalo_exibicao_s
            agora = time.perf_counter()
            if agora - inicio_ciclo >= config.ORCAMENTO_CICLO_S:
                break  # estourou o orçamento: devolve o controle à janela

        # Computador mais lento que o tempo real: não acumula "dívida" de frames.
        if self.instante_proximo_frame < agora:
            self.instante_proximo_frame = agora

        # -- atualiza a tela: o vídeo uma vez por ciclo, com o frame mais recente --
        if ultimo_frame is not None:
            interface.atualizar_video(ultimo_frame)
            interface.mostrar_status(f"Rastreando... t = {self.tempo_acumulado:.3f} s")

        # -- os gráficos são redesenhados com menos frequência (e sempre no fim) --
        if fim_do_video or agora - self.instante_ultimo_desenho_graficos >= config.INTERVALO_GRAFICOS_S:
            interface.atualizar_graficos(self.tempos, self.xs, self.ys)
            self.instante_ultimo_desenho_graficos = agora

        if fim_do_video:
            self._finalizar_rastreamento("Fim do video")

    def _finalizar_rastreamento(self, motivo):
        """Fecha o CSV, mostra os gráficos completos e entra em ESTADO_FIM."""
        interface.atualizar_graficos(self.tempos, self.xs, self.ys)
        self._fechar_csv()
        self.estado = ESTADO_FIM
        self._atualizar_botoes()
        interface.mostrar_status(
            f"{motivo} - {len(self.tempos)} pontos salvos em:\n{self.caminho_csv}\n"
            "Use 'Remarcar objeto' ou 'Selecionar video' para fazer outra medida."
        )

    # ==================================================================
    # AUXILIARES
    # ==================================================================

    def _atualizar_botoes(self):
        """Habilita só os botões que fazem sentido no estado atual."""
        estado_atual = self.estado
        sem_dialogo_aberto = self._escolha_pendente is None  # com o diálogo aberto, tudo fica desabilitado
        interface.habilitar_botoes(
            selecionar=sem_dialogo_aberto and estado_atual != ESTADO_RASTREANDO,
            iniciar=sem_dialogo_aberto and estado_atual == ESTADO_MARCANDO and self.roi_painel is not None,
            parar=estado_atual == ESTADO_RASTREANDO,
            remarcar=sem_dialogo_aberto and estado_atual in (ESTADO_MARCANDO, ESTADO_FIM),
        )

    def _fechar_csv(self):
        if self.exportador is not None:
            self.exportador.fechar()
            self.exportador = None

    def _liberar_video(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None


def main():
    app = Aplicacao()
    try:
        app.executar()
    finally:
        app.encerrar()   # roda mesmo se a janela for fechada ou ocorrer um erro


if __name__ == "__main__":
    main()