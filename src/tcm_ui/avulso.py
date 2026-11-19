"""Executa um único módulo como aplicativo independente."""
from __future__ import annotations

import getpass
import sys

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from tcm_ui.atualizacao_ui import VerificadorAtualizacao
from tcm_ui.janela import JanelaPrincipal
from tcm_ui.modulo import Modulo
from tcm_ui.themes import tema


def rodar_avulso(modulo: Modulo, argv: list[str] | None = None) -> int:
    app = QApplication.instance() or QApplication(sys.argv if argv is None else argv)
    tema.configurar("TCM", modulo.aplicacao_settings)
    tema.aplicar(app)
    janela = JanelaPrincipal([modulo], nome_app=modulo.nome, icone_app=modulo.icone,
                             usuario=getpass.getuser(), modo="avulso",
                             configuracoes=QSettings("TCM", modulo.aplicacao_settings),
                             rodape=[f"Versão {modulo.versao}"])
    VerificadorAtualizacao(janela, modulo.repositorio, modulo.nome_exe, modulo.versao).iniciar()
    janela.show()
    return app.exec()
