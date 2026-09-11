# -*- coding: utf-8 -*-
"""
Escreve os dados, tempo, posição X e posição Y
Em colunas, para ser usado outra forma de analisar os dados
"""


class ExportadorCSV:
    def __init__(self, caminho_saida: str):
        self._arquivo = open(caminho_saida, "w", newline="", encoding="utf-8")
        self._arquivo.write("Tempo,X,Y\n")

    def registrar(self, tempo_s: float, x_m: float, y_m: float) -> None:
        self._arquivo.write(f"{tempo_s},{x_m},{y_m}\n")

    def fechar(self) -> None:
        self._arquivo.close()

    # Suporte a "with ExportadorCSV(...) as exportador:"
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.fechar()
