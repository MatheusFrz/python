# -*- coding: utf-8 -*-
"""
exportador_csv.py - grava as medições em arquivo CSV.

Formato do arquivo (uma linha por frame rastreado):
    Tempo,X,Y
    0.0,0.0353,0.1766
    ...
    Tempo em segundos; X e Y em metros (ver conversao.py).

Serve para analisar os dados depois em outro programa (Excel, Python etc.).

Uso recomendado, que fecha o arquivo mesmo em caso de erro:
    with ExportadorCSV("saida.csv") as exportador:
        exportador.registrar(t, x, y)

Usado por: main.py.
"""


class ExportadorCSV:
    def __init__(self, caminho_saida: str):
        """Cria (ou sobrescreve) o arquivo e escreve o cabeçalho."""
        self._arquivo = open(caminho_saida, "w", newline="", encoding="utf-8")
        self._arquivo.write("Tempo,X,Y\n")

    def registrar(self, tempo_s: float, x_m: float, y_m: float) -> None:
        """Acrescenta uma linha: instante (s) e posição (m)."""
        self._arquivo.write(f"{tempo_s},{x_m},{y_m}\n")

    def fechar(self) -> None:
        self._arquivo.close()

    # -- suporte ao "with ExportadorCSV(...) as exportador:" --
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.fechar()