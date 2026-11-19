"""Garante que a vitrine (`python -m tcm_ui.demo`) não quebra em silêncio."""
from PySide6.QtWidgets import QWidget

from tcm_ui import demo
from tcm_ui.modulo import Contexto, Modulo


def test_modulo_vitrine_valido():
    assert isinstance(demo.MODULO, Modulo)
    assert demo.MODULO.id == "vitrine"
    assert [p.chave for p in demo.MODULO.paginas] == ["painel", "componentes", "config"]


def test_cada_pagina_da_vitrine_e_criada(qtbot):
    import logging
    from pathlib import Path

    host = QWidget()
    qtbot.addWidget(host)
    ctx = Contexto(usuario="teste", pasta_dados=Path("."), modo="avulso",
                   log=logging.getLogger("vitrine"), janela=host)
    instancia = demo.MODULO.criar(ctx)
    for pagina in demo.MODULO.paginas:
        widget = instancia.widget(pagina.chave)
        qtbot.addWidget(widget)
        assert isinstance(widget, QWidget)
        assert all(isinstance(a, QWidget) for a in instancia.acoes_cabecalho(pagina.chave))
    assert instancia.pode_fechar()
