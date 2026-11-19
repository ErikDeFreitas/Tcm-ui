import os
import sys
from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from conftest import fazer_modulo
from tcm_ui import atualizacao_ui, avulso
from tcm_ui.atualizacao_ui import VerificadorAtualizacao
from tcm_ui.atualizador import ErroAtualizacao
from tcm_ui.components import Texto


def _preparar(monkeypatch, janela, tarefas=()):
    jan = janela([fazer_modulo()])
    monkeypatch.setattr(jan, "modulos_com_tarefa", lambda: list(tarefas))
    chamadas = {"aplicar": [], "informar": [], "fechar": 0, "saida": []}
    monkeypatch.setattr(atualizacao_ui.atualizador, "aplicar_e_reiniciar",
                        lambda novo, *a, **k: chamadas["aplicar"].append(novo))
    monkeypatch.setattr(atualizacao_ui.Modal, "informar",
                        lambda *a, **k: chamadas["informar"].append(a))
    monkeypatch.setattr(atualizacao_ui.os, "_exit", lambda c: chamadas["saida"].append(c))
    monkeypatch.setattr(jan, "close", lambda: chamadas.__setitem__("fechar", chamadas["fechar"] + 1))
    return jan, chamadas


def test_nao_congelado_nao_busca(qtbot, monkeypatch, janela):
    jan, _ = _preparar(monkeypatch, janela)
    buscas = []
    monkeypatch.setattr(atualizacao_ui.atualizador, "buscar_atualizacao",
                        lambda *a: buscas.append(a))
    monkeypatch.setattr(atualizacao_ui.atualizador, "limpar_temporarios",
                        lambda *a: buscas.append("limpar"))
    ver = VerificadorAtualizacao(jan, "Dono/Repo", "Falso.exe", "1.0.0", congelado=False)
    ver.iniciar()
    assert buscas == []


def test_congelado_busca_baixa_e_emite_pronto(qtbot, monkeypatch, janela):
    jan, _ = _preparar(monkeypatch, janela)
    info = {"versao": "1.1.0", "url_exe": "x", "url_sha": "y"}
    baixados = []
    monkeypatch.setattr(atualizacao_ui.atualizador, "limpar_temporarios", lambda *a: None)
    monkeypatch.setattr(atualizacao_ui.atualizador, "buscar_atualizacao", lambda *a: info)
    monkeypatch.setattr(atualizacao_ui.atualizador, "baixar_e_verificar",
                        lambda i, destino: baixados.append((i, destino)))
    ver = VerificadorAtualizacao(jan, "Dono/Repo", "Falso.exe", "1.0.0", congelado=True)
    with qtbot.waitSignal(ver.pronto, timeout=5000) as sinal:
        ver.iniciar()
    assert sinal.args == ["1.1.0", sys.executable + ".novo"]
    assert baixados == [(info, Path(sys.executable + ".novo"))]


def test_adiar_quando_ha_tarefa(qtbot, monkeypatch, tmp_path, janela):
    jan, chamadas = _preparar(monkeypatch, janela, tarefas=["M1"])
    novo = tmp_path / "Falso.exe.novo"
    novo.write_bytes(b"x")
    ver = VerificadorAtualizacao(jan, "Dono/Repo", "Falso.exe", "1.0.0", congelado=True)
    ver.pronto.emit("1.1.0", str(novo))
    assert not novo.exists()
    assert chamadas["aplicar"] == []
    assert chamadas["informar"] == []
    assert chamadas["saida"] == []


def test_aplica_quando_livre(qtbot, monkeypatch, tmp_path, janela):
    jan, chamadas = _preparar(monkeypatch, janela)
    novo = tmp_path / "Falso.exe.novo"
    novo.write_bytes(b"x")
    ver = VerificadorAtualizacao(jan, "Dono/Repo", "Falso.exe", "1.0.0", congelado=True)
    ver.pronto.emit("1.1.0", str(novo))
    assert chamadas["aplicar"] == [novo]
    assert chamadas["informar"][0][3] == "sucesso"
    assert "1.1.0" in chamadas["informar"][0][2]
    assert chamadas["fechar"] == 1
    assert chamadas["saida"] == [0]


def test_erro_ao_aplicar_apaga_novo_e_avisa(qtbot, monkeypatch, tmp_path, janela):
    jan, chamadas = _preparar(monkeypatch, janela)

    def falhar(novo, *a, **k):
        raise ErroAtualizacao("sem permissão")

    monkeypatch.setattr(atualizacao_ui.atualizador, "aplicar_e_reiniciar", falhar)
    novo = tmp_path / "Falso.exe.novo"
    novo.write_bytes(b"x")
    ver = VerificadorAtualizacao(jan, "Dono/Repo", "Falso.exe", "1.0.0", congelado=True)
    ver.pronto.emit("1.1.0", str(novo))
    assert not novo.exists()
    assert len(chamadas["informar"]) == 2  # "instalada" e depois o erro
    erro = chamadas["informar"][-1]
    assert erro[3] == "perigo"
    assert "sem permissão" in erro[2] and "continuará na versão atual" in erro[2]
    assert chamadas["fechar"] == 0
    assert chamadas["saida"] == []


def test_rodar_avulso_configura_tema_e_janela(qtbot, monkeypatch, qapp):
    modulo = fazer_modulo()
    configurado, janelas = [], []
    monkeypatch.setattr(avulso.tema, "configurar", lambda org, app: configurado.append((org, app)))
    monkeypatch.setattr(avulso.tema, "aplicar", lambda app: None)
    monkeypatch.setattr(avulso.VerificadorAtualizacao, "iniciar", lambda self: None)
    original_show = avulso.JanelaPrincipal.show

    def mostrar(self):
        janelas.append(self)
        original_show(self)

    monkeypatch.setattr(avulso.JanelaPrincipal, "show", mostrar)
    monkeypatch.setattr(QApplication, "exec", staticmethod(lambda: 0))
    try:
        assert avulso.rodar_avulso(modulo) == 0
        assert configurado == [("TCM", "Falso")]
        assert len(janelas) == 1
        jan = janelas[0]
        qtbot.addWidget(jan)
        assert list(jan._modulos) == ["falso"]
        assert jan._modo == "avulso"
        assert [t for t in jan.findChildren(Texto) if t.property("papel") == "secao"] == []
        jan.close()
    finally:
        QSettings("TCM", "Falso").clear()
