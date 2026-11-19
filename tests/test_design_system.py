import re
import pytest
from PySide6.QtCore import QSettings
from importlib.metadata import version
import tcm_ui
from tcm_ui.themes import tema, TEMAS

def test_versao_do_pacote_igual_a_do_codigo():
    assert version("tcm-ui") == tcm_ui.__version__ == "1.0.0"

def test_qss_sem_token_nao_resolvido(qapp):
    for nome in TEMAS:
        tema._nome = nome
        qss = tema._qss(tema.tokens())
        assert not re.search(r"@[a-z]", qss), f"token sem valor no tema {nome}"

def test_aplicar_tema_define_stylesheet_e_fusion(qapp):
    tema.aplicar(qapp)
    assert qapp.styleSheet()
    # com stylesheet ativo, style() devolve o proxy QStyleSheetStyle (name() vazio);
    # remove o QSS para inspecionar o estilo base.
    qapp.setStyleSheet("")
    assert qapp.style().name().lower() == "fusion"

def test_alternar_emite_mudou(qtbot):
    tema._nome = "claro"
    with qtbot.waitSignal(tema.mudou) as sinal:
        tema.alternar()
    assert sinal.args == ["escuro"] and tema.escuro

def test_configurar_le_preferencia_salva(qapp):
    QSettings("TCM-teste", "AppA").setValue("aparencia/tema", "escuro")
    tema.configurar("TCM-teste", "AppA")
    assert tema.nome == "escuro"

def test_definir_grava_na_aplicacao_configurada(qapp):
    tema.configurar("TCM-teste", "AppB")
    tema.definir("escuro")
    assert QSettings("TCM-teste", "AppB").value("aparencia/tema") == "escuro"

def test_valor_invalido_vira_claro(qapp):
    QSettings("TCM-teste", "AppC").setValue("aparencia/tema", "roxo")
    tema.configurar("TCM-teste", "AppC")
    assert tema.nome == "claro"


@pytest.mark.parametrize("organizacao, aplicacao", [("TCM-teste", "Janela"), ("TCM", "Falso")])
def test_qsettings_dos_testes_nao_usam_o_registro(organizacao, aplicacao):
    config = QSettings(organizacao, aplicacao)
    assert config.format() == QSettings.IniFormat
    assert "HKEY_" not in config.fileName().upper()


def test_qsettings_do_pacote_nao_usam_o_registro():
    from tcm_ui import avulso

    tema.configurar("TCM-teste", "AppA")
    assert tema._config.format() == QSettings.IniFormat
    assert avulso.QSettings is QSettings
