"""Janela principal: barra lateral + cabeçalho + páginas dos módulos (casca ou avulso)."""
from __future__ import annotations

import logging
import traceback
from collections.abc import Sequence
from typing import Literal

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QScrollArea, QStackedWidget, QVBoxLayout, QWidget

from . import icons
from .components import BarraLateral, BotaoTema, Cabecalho, CartaoErro, EstadoVazio, Modal, Pagina, Texto
from .modulo import Contexto, InstanciaModulo, Modulo
from .themes import MARCA, TAMANHOS

_CHAVE_ULTIMA = "navegacao/ultima"


class JanelaPrincipal(QMainWindow):
    def __init__(self, modulos: Sequence[Modulo], *, nome_app: str, icone_app: str, usuario: str,
                 modo: Literal["casca", "avulso"], configuracoes: QSettings,
                 rodape: Sequence[str] = (),
                 sem_modulos: tuple[str, str] = ("Nenhum sistema disponível", "")):
        ids = [m.id for m in modulos]
        repetidos = sorted({i for i in ids if ids.count(i) > 1})
        if repetidos:
            raise ValueError(f"id de módulo repetido: {repetidos}")
        super().__init__()
        self._modulos = {m.id: m for m in modulos}
        self._usuario, self._modo, self._configuracoes = usuario, modo, configuracoes
        self._instancias: dict[str, InstanciaModulo] = {}
        self._falhas: dict[str, str] = {}  # id -> traceback/motivo da falha em criar
        self._paginas: dict[tuple[str, str], QWidget] = {}
        self._acoes_paginas: dict[tuple[str, str], list[QWidget]] = {}  # acoes_cabecalho: 1 vez por página
        self._atual: tuple[str, str] | None = None

        self.setWindowTitle(nome_app)
        self.setWindowIcon(icons.icone(icone_app, MARCA["primaria"], 32))
        self.resize(TAMANHOS["janela_largura"], TAMANHOS["janela_altura"])
        self.setMinimumSize(TAMANHOS["janela_min_largura"], TAMANHOS["janela_min_altura"])

        self._barra = BarraLateral(nome_app, icone_app)
        for modulo in modulos:
            if len(modulos) > 1:
                self._barra.adicionar_secao(modulo.nome)
            for pagina in modulo.paginas:
                self._barra.adicionar_item(f"{modulo.id}:{pagina.chave}", pagina.titulo, pagina.icone)
        for linha in rodape:
            self._barra.adicionar_rodape(Texto(linha, "dica"))
        self._barra.navegou.connect(self._navegou)

        self._cabecalho = Cabecalho()
        self._botao_tema = BotaoTema()
        self._cabecalho.adicionar(self._botao_tema)
        self._stack = QStackedWidget()

        direita = QVBoxLayout()
        direita.setContentsMargins(0, 0, 0, 0)
        direita.setSpacing(0)
        direita.addWidget(self._cabecalho)
        direita.addWidget(self._stack, 1)
        raiz = QHBoxLayout()
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)
        raiz.addWidget(self._barra)
        raiz.addLayout(direita, 1)
        central = QWidget()
        central.setLayout(raiz)
        self.setCentralWidget(central)

        chaves = self._barra.chaves()
        if not chaves:
            self._stack.addWidget(EstadoVazio(*sem_modulos, icone="alerta"))
            return
        ultima = configuracoes.value(_CHAVE_ULTIMA)
        inicial = ultima if ultima in chaves else chaves[0]
        self.abrir(*inicial.split(":", 1))

    # ------------------------------------------------------------ navegação

    def abrir(self, id_modulo: str, chave: str) -> None:
        modulo = self._modulos[id_modulo]
        pagina = next(p for p in modulo.paginas if p.chave == chave)
        alvo = (id_modulo, chave)
        if alvo not in self._paginas:
            self._paginas[alvo] = self._montar(modulo, chave)
            self._stack.addWidget(self._paginas[alvo])
        self._stack.setCurrentWidget(self._paginas[alvo])
        self._atual = alvo

        self._barra.blockSignals(True)  # selecionar emite navegou, que voltaria aqui
        self._barra.selecionar(f"{id_modulo}:{chave}")
        self._barra.blockSignals(False)
        self._cabecalho.definir_titulo(pagina.titulo, pagina.subtitulo)
        self._cabecalho.limpar_acoes()
        for acao in self._acoes(modulo, alvo):
            self._cabecalho.adicionar(acao)
        self._cabecalho.adicionar(self._botao_tema)
        self._configuracoes.setValue(_CHAVE_ULTIMA, f"{id_modulo}:{chave}")

    def _navegou(self, chave_item: str) -> None:
        self.abrir(*chave_item.split(":", 1))

    @property
    def pagina_atual(self) -> tuple[str, str] | None:
        return self._atual

    @property
    def instancias(self) -> dict[str, InstanciaModulo]:
        return dict(self._instancias)

    # ------------------------------------------------------------ módulos

    def _log(self, modulo: Modulo) -> logging.Logger:
        nome = f"sistema_financeiro.{modulo.id}" if self._modo == "casca" else modulo.id
        return logging.getLogger(nome)

    def _instancia(self, modulo: Modulo) -> InstanciaModulo | None:
        """Cria o módulo no primeiro acesso; se `criar` falhou (ou devolveu None), não tenta de novo."""
        if modulo.id not in self._instancias and modulo.id not in self._falhas:
            try:
                contexto = Contexto(usuario=self._usuario, pasta_dados=modulo.pasta_dados, modo=self._modo,
                                    log=self._log(modulo), janela=self)
                instancia = modulo.criar(contexto)
            except Exception:
                self._log(modulo).exception("Erro ao criar o módulo %s", modulo.id)
                self._falhas[modulo.id] = traceback.format_exc()
            else:
                if instancia is None:
                    self._log(modulo).error("criar() do módulo %s devolveu None", modulo.id)
                    self._falhas[modulo.id] = "criar() devolveu None"
                else:
                    self._instancias[modulo.id] = instancia
        return self._instancias.get(modulo.id)

    def _montar(self, modulo: Modulo, chave: str) -> QWidget:
        """Monta a página; qualquer erro do módulo vira um CartaoErro (nunca derruba a janela)."""
        titulo_pagina = f"Não foi possível abrir esta página do {modulo.nome}"
        try:
            instancia = self._instancia(modulo)
            if instancia is None:
                widget = CartaoErro(f"Não foi possível abrir o {modulo.nome}", self._falhas[modulo.id])
            else:
                try:
                    widget = instancia.widget(chave)
                except Exception:
                    self._log(modulo).exception("Erro ao abrir a página %s:%s", modulo.id, chave)
                    widget = CartaoErro(titulo_pagina, traceback.format_exc())
                else:
                    if not isinstance(widget, QWidget):
                        motivo = f"widget() devolveu {type(widget).__name__}"
                        self._log(modulo).error("Erro ao abrir a página %s:%s: %s", modulo.id, chave, motivo)
                        widget = CartaoErro(titulo_pagina, motivo)
            if isinstance(widget, QScrollArea):
                return widget
            pagina = Pagina()
            pagina.conteudo.addWidget(widget)
            return pagina
        except Exception:  # rede de segurança: falha ao embrulhar o widget do módulo
            self._log(modulo).exception("Erro ao montar a página %s:%s", modulo.id, chave)
            pagina = Pagina()
            pagina.conteudo.addWidget(CartaoErro(titulo_pagina, traceback.format_exc()))
            return pagina

    def _acoes(self, modulo: Modulo, alvo: tuple[str, str]) -> list[QWidget]:
        """Ações do cabeçalho da página; `acoes_cabecalho` é chamado uma vez por página e reaproveitado."""
        if alvo not in self._acoes_paginas:
            instancia = self._instancias.get(modulo.id)
            acoes: list[QWidget] = []
            if instancia is not None:
                try:
                    acoes = list(instancia.acoes_cabecalho(alvo[1]))
                    invalidas = [type(a).__name__ for a in acoes if not isinstance(a, QWidget)]
                    if invalidas:
                        raise TypeError(f"acoes_cabecalho() devolveu itens que não são QWidget: {invalidas}")
                except Exception:
                    self._log(modulo).exception("Erro nas ações do cabeçalho de %s:%s", *alvo)
                    acoes = []
            self._acoes_paginas[alvo] = acoes
        return self._acoes_paginas[alvo]

    # ------------------------------------------------------------ fechamento

    def modulos_com_tarefa(self) -> list[str]:
        nomes = []
        for id_modulo, instancia in self._instancias.items():
            modulo = self._modulos[id_modulo]
            try:
                livre = instancia.pode_fechar()
            except Exception:
                self._log(modulo).exception("Erro em pode_fechar de %s", id_modulo)
                livre = False
            if not livre:
                nomes.append(modulo.nome)
        return nomes

    def closeEvent(self, evento) -> None:
        nomes = self.modulos_com_tarefa()
        if nomes and not Modal.confirmar(
                self, "Fechar o programa?",
                f"Há uma tarefa em andamento em: {', '.join(nomes)}. Se fechar agora, ela será interrompida.",
                "Fechar mesmo assim"):
            evento.ignore()
            return
        super().closeEvent(evento)
