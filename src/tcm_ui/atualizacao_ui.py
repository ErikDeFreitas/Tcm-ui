"""Verificação de atualização em segundo plano e aplicação com aviso ao usuário."""
from __future__ import annotations

import logging
import os
import sys
import threading
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from tcm_ui import atualizador
from tcm_ui.components import Modal
from tcm_ui.janela import JanelaPrincipal

_log = logging.getLogger("tcm_ui.atualizacao")


class VerificadorAtualizacao(QObject):
    pronto = Signal(str, str)  # versao, caminho do .novo

    def __init__(self, janela: JanelaPrincipal, repositorio: str, nome_exe: str, versao_atual: str,
                 congelado: bool | None = None):
        super().__init__(janela)
        self._janela = janela
        self._repositorio, self._nome_exe, self._versao_atual = repositorio, nome_exe, versao_atual
        self._congelado = getattr(sys, "frozen", False) if congelado is None else congelado
        self.pronto.connect(self._ao_pronto)

    def iniciar(self) -> None:
        """Só no executável: limpa sobras e procura Release mais nova numa thread daemon."""
        if not self._congelado:
            return
        atualizador.limpar_temporarios()
        threading.Thread(target=self._buscar, daemon=True).start()

    def _buscar(self) -> None:
        try:
            info = atualizador.buscar_atualizacao(self._repositorio, self._nome_exe, self._versao_atual)
            if not info:
                return
            _log.info("Nova versão %s encontrada. Baixando...", info["versao"])
            novo = Path(sys.executable + ".novo")
            atualizador.baixar_e_verificar(info, novo)
            self.pronto.emit(info["versao"], str(novo))
        except atualizador.ErroAtualizacao as e:
            _log.warning("Atualização automática não realizada: %s", e)
        except Exception as e:
            _log.warning("Atualização automática não realizada (%s).", type(e).__name__, exc_info=True)

    def _ao_pronto(self, versao: str, caminho: str) -> None:
        novo = Path(caminho)
        if self._janela.modulos_com_tarefa():  # nunca troca o programa no meio de uma tarefa
            novo.unlink(missing_ok=True)
            _log.info("Atualização adiada: tarefa em andamento")
            return
        Modal.informar(self._janela, "Atualização",
                       f"Nova versão {versao} instalada.\nO programa será reiniciado agora.", "sucesso")
        try:
            atualizador.aplicar_e_reiniciar(novo)
        except atualizador.ErroAtualizacao as e:
            novo.unlink(missing_ok=True)
            Modal.informar(self._janela, "Atualização",
                           f"{e}\nO programa continuará na versão atual.", "perigo")
            return
        self._janela.close()
        os._exit(0)
