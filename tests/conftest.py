import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6 import QtCore


class _QSettingsIni(QtCore.QSettings):
    """QSettings(org, app) em arquivo .ini (pasta temporária), nunca no registro do Windows.

    No Qt 6, QSettings(org, app) ignora setDefaultFormat() e usa sempre o registro; por isso a classe é
    trocada em PySide6.QtCore antes de qualquer `from PySide6.QtCore import QSettings` (testes e tcm_ui).
    """

    def __init__(self, *args, **kwargs):
        if 1 <= len(args) <= 2 and not kwargs and all(isinstance(a, str) for a in args):
            super().__init__(QtCore.QSettings.IniFormat, QtCore.QSettings.UserScope, *args)
        else:
            super().__init__(*args, **kwargs)


QtCore.QSettings = _QSettingsIni
from PySide6.QtCore import QSettings  # noqa: E402  (já é a _QSettingsIni)

from tcm_ui.themes import tema  # noqa: E402

# Aplicações usadas pelos testes em QSettings("TCM-teste", ...); acrescente as das próximas tasks.
_APLICACOES_TESTE = ("AppA", "AppB", "AppC", "Janela")


@pytest.fixture(autouse=True, scope="session")
def _qsettings_fora_do_registro(tmp_path_factory):
    """Toda QSettings(org, app) dos testes vira arquivo .ini numa pasta temporária, nunca o registro real."""
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(tmp_path_factory.mktemp("qsettings")))


@pytest.fixture(autouse=True)
def _isolar_estado_global():
    """Restaura o singleton `tema` e limpa as QSettings de teste, para os testes não dependerem de ordem."""
    nome, config = tema._nome, tema._config
    yield
    tema._nome, tema._config = nome, config
    for aplicacao in _APLICACOES_TESTE:
        QSettings("TCM-teste", aplicacao).clear()


@pytest.fixture
def janela(qtbot):
    """Fábrica `janela(modulos, **kw)` de `JanelaPrincipal` com configurações de teste."""
    from tcm_ui.janela import JanelaPrincipal

    def fabricar(modulos, **kw):
        opcoes = dict(
            nome_app="Teste",
            icone_app="painel",
            usuario="TCMSP\\teste",
            modo="casca",
            configuracoes=QSettings("TCM-teste", "Janela"),
        )
        opcoes.update(kw)
        jan = JanelaPrincipal(modulos, **opcoes)
        qtbot.addWidget(jan)
        return jan

    return fabricar


def fazer_modulo(**trocas):
    """Cria um `Modulo` válido com instância falsa; `trocas` sobrescreve campos.

    Importável de outros testes: `from conftest import fazer_modulo`.
    """
    from pathlib import Path

    from PySide6.QtWidgets import QLabel, QWidget

    from tcm_ui.modulo import Modulo, Pagina

    class InstanciaFalsa:
        def __init__(self, contexto):
            self.contexto = contexto
            self._widgets: dict[str, QWidget] = {}

        def widget(self, chave_pagina: str) -> QWidget:
            if chave_pagina not in self._widgets:
                self._widgets[chave_pagina] = QLabel(chave_pagina)
            return self._widgets[chave_pagina]

        def acoes_cabecalho(self, chave_pagina: str) -> list[QWidget]:
            return []

        def pode_fechar(self) -> bool:
            return True

    campos = dict(
        id="falso",
        nome="Falso",
        icone="",
        versao="1.0.0",
        grupo_ad="SF-Falso",
        repositorio="ErikDeFreitas/Falso",
        nome_exe="Falso.exe",
        pasta_dados=Path("dados_falsos"),
        paginas=(Pagina("a", "A", "", ""), Pagina("b", "B", "", "")),
        criar=InstanciaFalsa,
    )
    campos.update(trocas)
    return Modulo(**campos)
