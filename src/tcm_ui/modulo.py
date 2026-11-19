"""Contrato que cada aplicativo financeiro implementa para rodar na casca ou avulso."""
from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from PySide6.QtWidgets import QWidget

from .atualizador import PADRAO_REPOSITORIO

_PADRAO_ID = re.compile(r"[a-z][a-z0-9_]*")  # usar com fullmatch


@dataclass(frozen=True)
class Pagina:
    chave: str
    titulo: str
    subtitulo: str
    icone: str


@dataclass(frozen=True)
class Contexto:
    usuario: str  # "TCMSP\fulano" (casca) ou login do Windows (avulso)
    pasta_dados: Path  # = Modulo.pasta_dados
    modo: Literal["casca", "avulso"]
    log: logging.Logger
    janela: QWidget  # pai para Modal e QFileDialog


class InstanciaModulo(Protocol):
    def widget(self, chave_pagina: str) -> QWidget: ...
    def acoes_cabecalho(self, chave_pagina: str) -> list[QWidget]: ...
    def pode_fechar(self) -> bool: ...


@dataclass(frozen=True)
class Modulo:
    id: str
    nome: str
    icone: str
    versao: str
    grupo_ad: str  # ex.: "SF-RoboAgregado"
    repositorio: str  # "Dono/Repo"
    nome_exe: str  # termina em ".exe"
    pasta_dados: Path  # onde o sistema já guarda dados hoje
    paginas: tuple[Pagina, ...]  # não vazia, chaves únicas
    criar: Callable[[Contexto], InstanciaModulo]

    def __post_init__(self) -> None:
        if not _PADRAO_ID.fullmatch(self.id):
            raise ValueError(f"id inválido: {self.id!r} (esperado ^[a-z][a-z0-9_]*$)")
        if not self.paginas:
            raise ValueError("paginas não pode ser vazia")
        chaves = [p.chave for p in self.paginas]
        if len(set(chaves)) != len(chaves):
            raise ValueError(f"chave de página repetida em paginas: {chaves}")
        if not self.nome_exe.lower().endswith(".exe"):
            raise ValueError(f"nome_exe deve terminar em .exe: {self.nome_exe!r}")
        if not PADRAO_REPOSITORIO.fullmatch(self.repositorio):
            raise ValueError(f"repositorio deve ser 'Dono/Repo': {self.repositorio!r}")

    @property
    def aplicacao_settings(self) -> str:
        return Path(self.nome_exe).stem
