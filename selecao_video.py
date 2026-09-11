# -*- coding: utf-8 -*-
"""
Responsável apenas por abrir o diálogo de seleção de arquivo.
"""

import tkinter as tk
from tkinter import filedialog
from pathlib import Path


def selecionar_arquivo_video() -> str:
    """Abre um diálogo para o usuário escolher um vídeo e retorna o caminho."""
    root = tk.Tk()
    root.withdraw()  # abre o tkinter em segundo plano, apenas para usar o filedialog

    caminho = filedialog.askopenfilename(
        title="Selecione o vídeo",
        filetypes=[("Vídeos", "*.mp4 *.avi *.mov *.mkv")]
    )
    root.destroy()
    return caminho


def nome_base(caminho_video: str) -> str:
    """Extrai o nome do arquivo sem a extensão, usado para nomear a saída."""
    return Path(caminho_video).stem
