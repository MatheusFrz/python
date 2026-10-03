# -*- coding: utf-8 -*-
"""
selecao_video.py - diálogo do sistema para escolher o arquivo de vídeo.

Papel:
    Abre a janela "Abrir arquivo" nativa do sistema operacional.

Por que roda em outro processo (escolher_video_nativo):
    O tkinter (que desenha esse diálogo) e o DearPyGui (a janela principal)
    não se dão bem no mesmo processo, e o diálogo bloquearia o loop da janela
    enquanto o usuário escolhe. Num processo separado, a janela principal
    continua respondendo. O tkinter também só é importado quando necessário,
    então o programa funciona (com o diálogo do DearPyGui) mesmo sem ele.

Usado por: main.py (escolher_video_nativo).
"""

import os
import subprocess
import sys
from pathlib import Path


def selecionar_arquivo_video() -> str:
    """
    Mostra o diálogo e retorna o caminho escolhido ("" se cancelar).
    Esta função BLOQUEIA até o usuário decidir; por isso o main.py só a
    chama indiretamente, por escolher_video_nativo().
    """
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()  # esconde a janela vazia do tkinter; só o diálogo aparece
    root.attributes("-topmost", True)  # o diálogo aparece na frente da janela principal

    caminho = filedialog.askopenfilename(
        title="Selecione o vídeo",
        filetypes=[("Vídeos", "*.mp4 *.avi *.mov *.mkv")]
    )
    root.destroy()
    return caminho


def escolher_video_nativo():
    """
    Executa selecionar_arquivo_video() num processo separado.

    Retorna:
        str não vazia -> caminho do vídeo escolhido
        ""            -> o usuário cancelou
        None          -> o diálogo nativo não está disponível (ex.: sem tkinter);
                         quem chamou deve usar outro tipo de diálogo
    """
    # código executado no processo filho: chama a função e imprime o resultado
    codigo_filho = "from selecao_video import selecionar_arquivo_video; print(selecionar_arquivo_video())"
    variaveis_ambiente = {**os.environ, "PYTHONIOENCODING": "utf-8"}  # acentos no caminho
    try:
        resultado = subprocess.run(
            [sys.executable, "-c", codigo_filho],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=variaveis_ambiente,
        )
    except OSError:
        return None
    if resultado.returncode != 0:
        return None
    return resultado.stdout.strip()


def nome_base(caminho_video: str) -> str:
    """(Sem uso atual; o main.py usa Path diretamente.) Nome do arquivo sem extensão."""
    return Path(caminho_video).stem