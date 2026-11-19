from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QLabel, QPushButton
import pytest

from conftest import fazer_modulo
from tcm_ui.components import BotaoTema, CartaoErro, EstadoVazio, Modal, Texto
from tcm_ui.janela import JanelaPrincipal

InstanciaBase = fazer_modulo().criar  # classe da instância falsa do conftest


def _dois_modulos(**trocas_m2):
    m1 = fazer_modulo(id="m1", nome="M1")
    m2 = fazer_modulo(**{"id": "m2", "nome": "M2", **trocas_m2})
    return [m1, m2]


def _pagina_mostrada(jan):
    return jan._stack.currentWidget()


def test_ids_repetidos_rejeitados(qtbot):
    with pytest.raises(ValueError, match="m1"):
        JanelaPrincipal([fazer_modulo(id="m1"), fazer_modulo(id="m1")], nome_app="Teste",
                        icone_app="painel", usuario="u", modo="casca",
                        configuracoes=QSettings("TCM-teste", "Janela"))


def _secoes(jan):
    return [t.text() for t in jan.findChildren(Texto) if t.property("papel") == "secao"]


def test_secoes_so_com_mais_de_um_modulo(janela):
    assert _secoes(janela([fazer_modulo(id="m1", nome="M1")])) == []
    assert _secoes(janela(_dois_modulos())) == ["M1", "M2"]


def test_barra_lateral_chaves_e_rodape(janela):
    jan = janela(_dois_modulos(), rodape=["Versão 1.0.0", "Usuário: teste"])
    assert jan._barra.chaves() == ["m1:a", "m1:b", "m2:a", "m2:b"]
    dicas = [t.text() for t in jan._barra.findChildren(Texto) if t.property("papel") == "dica"]
    assert dicas == ["Versão 1.0.0", "Usuário: teste"]
    assert jan.windowTitle() == "Teste"
    assert not jan.windowIcon().isNull()


def test_abre_na_primeira_pagina(janela):
    jan = janela(_dois_modulos())
    assert jan.pagina_atual == ("m1", "a")
    assert jan._cabecalho._titulo.text() == "A"


def test_criar_so_no_primeiro_acesso(janela):
    chamadas = []

    def criar(contexto):
        chamadas.append(contexto)
        return InstanciaBase(contexto)

    jan = janela(_dois_modulos(criar=criar))
    assert chamadas == []
    assert list(jan.instancias) == ["m1"]
    jan.abrir("m2", "a")
    primeiro = _pagina_mostrada(jan)
    jan.abrir("m1", "a")
    jan.abrir("m2", "a")
    jan.abrir("m2", "b")
    assert len(chamadas) == 1
    jan.abrir("m2", "a")
    assert _pagina_mostrada(jan) is primeiro
    assert jan.pagina_atual == ("m2", "a")


def test_contexto_recebe_dados_do_modulo(janela):
    jan = janela(_dois_modulos())
    contexto = jan.instancias["m1"].contexto
    assert contexto.usuario == "TCMSP\\teste"
    assert contexto.modo == "casca"
    assert contexto.pasta_dados == fazer_modulo().pasta_dados
    assert contexto.log.name == "sistema_financeiro.m1"
    assert contexto.janela is jan


def test_contexto_avulso_usa_log_pelo_id(janela):
    jan = janela([fazer_modulo(id="m1")], modo="avulso")
    assert jan.instancias["m1"].contexto.log.name == "m1"
    assert jan.instancias["m1"].contexto.modo == "avulso"


def test_erro_em_criar_mostra_cartao_e_resto_funciona(janela):
    chamadas = []

    def criar(contexto):
        chamadas.append(1)
        raise RuntimeError("banco fora do ar")

    jan = janela(_dois_modulos(criar=criar))
    jan.abrir("m2", "a")
    cartao = _pagina_mostrada(jan).findChild(CartaoErro)
    assert cartao.titulo == "Não foi possível abrir o M2"
    assert "banco fora do ar" in cartao.detalhes
    jan.abrir("m2", "b")
    assert _pagina_mostrada(jan).findChild(CartaoErro).titulo == "Não foi possível abrir o M2"
    assert len(chamadas) == 1  # sem nova tentativa
    assert "m2" not in jan.instancias
    jan.abrir("m1", "b")
    assert _pagina_mostrada(jan).findChild(QLabel).text() == "b"


def test_erro_em_uma_pagina_nao_afeta_outra(janela):
    class Instancia(InstanciaBase):
        def widget(self, chave_pagina):
            if chave_pagina == "a":
                raise RuntimeError("página quebrada")
            return super().widget(chave_pagina)

    jan = janela([fazer_modulo(id="m1", criar=Instancia)])
    cartao = _pagina_mostrada(jan).findChild(CartaoErro)
    assert "página quebrada" in cartao.detalhes
    jan.abrir("m1", "b")
    assert _pagina_mostrada(jan).findChild(CartaoErro) is None
    assert _pagina_mostrada(jan).findChild(QLabel).text() == "b"


def test_acoes_trocam_com_a_pagina(janela):
    botao = QPushButton("Exportar")

    class Instancia(InstanciaBase):
        def acoes_cabecalho(self, chave_pagina):
            return [botao] if chave_pagina == "a" else []

    jan = janela([fazer_modulo(id="m1", criar=Instancia)])
    tema = jan._cabecalho.findChild(BotaoTema)
    assert jan._cabecalho._acoes == [botao, tema]
    jan.abrir("m1", "b")
    assert botao.isHidden()
    assert jan._cabecalho._acoes == [tema]
    assert not tema.isHidden()
    jan.abrir("m1", "a")
    assert not botao.isHidden()
    assert jan._cabecalho._acoes == [botao, tema]


def test_erro_em_acoes_deixa_so_o_tema(janela):
    class Instancia(InstanciaBase):
        def acoes_cabecalho(self, chave_pagina):
            raise RuntimeError("falhou")

    jan = janela([fazer_modulo(id="m1", criar=Instancia)])
    assert [type(w) for w in jan._cabecalho._acoes] == [BotaoTema]
    assert _pagina_mostrada(jan).findChild(QLabel).text() == "a"


def test_lembra_ultima_pagina(janela):
    jan = janela(_dois_modulos())
    jan.abrir("m1", "b")
    assert QSettings("TCM-teste", "Janela").value("navegacao/ultima") == "m1:b"
    nova = janela(_dois_modulos())
    assert nova.pagina_atual == ("m1", "b")
    assert nova._barra._itens["m1:b"].isChecked()


def test_navegar_pela_barra_abre_pagina(janela):
    jan = janela(_dois_modulos())
    jan._barra._itens["m2:b"].click()
    assert jan.pagina_atual == ("m2", "b")


def test_ultima_pagina_invalida_cai_na_primeira(janela):
    QSettings("TCM-teste", "Janela").setValue("navegacao/ultima", "sumiu:x")
    jan = janela(_dois_modulos())
    assert jan.pagina_atual == ("m1", "a")


def test_sem_modulos_mostra_estado_vazio(janela):
    jan = janela([], sem_modulos=("Sem acesso", "Peça ao TI"), rodape=["Versão 1.0.0"])
    vazio = jan.findChild(EstadoVazio)
    assert vazio.titulo == "Sem acesso"
    assert vazio.descricao == "Peça ao TI"
    assert jan._barra.chaves() == []
    assert jan.pagina_atual is None
    assert jan.instancias == {}


class InstanciaOcupada(InstanciaBase):
    ocupada = True

    def pode_fechar(self):
        return not InstanciaOcupada.ocupada


def test_fechar_com_tarefa_pede_confirmacao(janela, monkeypatch):
    pedidos = []

    def confirmar(parent, titulo, descricao, texto_ok="Confirmar", **_):
        pedidos.append((parent, titulo, descricao, texto_ok))
        return False

    monkeypatch.setattr(Modal, "confirmar", confirmar)
    InstanciaOcupada.ocupada = True
    jan = janela(_dois_modulos(criar=InstanciaOcupada))
    jan.abrir("m2", "a")
    jan.show()
    try:
        assert jan.close() is False
        assert jan.isVisible()
        assert pedidos == [(jan, "Fechar o programa?",
                            "Há uma tarefa em andamento em: M2. Se fechar agora, ela será interrompida.",
                            "Fechar mesmo assim")]
    finally:
        InstanciaOcupada.ocupada = False  # o qtbot fecha a janela no fim sem abrir modal
    assert jan.close() is True


def test_pode_fechar_com_excecao_conta_como_veto(janela):
    estado = {"quebrado": True}

    class Instancia(InstanciaBase):
        def pode_fechar(self):
            if estado["quebrado"]:
                raise RuntimeError("estado inconsistente")
            return True

    jan = janela(_dois_modulos())  # m2 nunca é criado: não entra na conta
    jan2 = janela([fazer_modulo(id="m1", nome="M1", criar=Instancia)])
    try:
        assert jan.modulos_com_tarefa() == []
        assert jan2.modulos_com_tarefa() == ["M1"]
    finally:
        estado["quebrado"] = False


# ------------------------------------------------------------ robustez (revisão final)

def _registros_com_excecao(caplog, nome_logger):
    return [r for r in caplog.records if r.name == nome_logger and r.levelname == "ERROR" and r.exc_info]


def test_criar_devolvendo_none_mostra_cartao_e_resto_funciona(janela):
    jan = janela(_dois_modulos(criar=lambda contexto: None))
    jan.abrir("m2", "a")
    cartao = _pagina_mostrada(jan).findChild(CartaoErro)
    assert cartao.titulo == "Não foi possível abrir o M2"
    assert "None" in cartao.detalhes
    assert "m2" not in jan.instancias
    jan.abrir("m1", "b")
    assert _pagina_mostrada(jan).findChild(QLabel).text() == "b"


def test_criar_devolvendo_none_na_primeira_pagina_nao_impede_abrir(janela):
    jan = janela([fazer_modulo(id="m1", nome="M1", criar=lambda contexto: None),
                  fazer_modulo(id="m2", nome="M2")])
    assert jan.pagina_atual == ("m1", "a")
    assert _pagina_mostrada(jan).findChild(CartaoErro).titulo == "Não foi possível abrir o M1"
    jan.abrir("m2", "a")
    assert _pagina_mostrada(jan).findChild(QLabel).text() == "a"


@pytest.mark.parametrize("devolvido, tipo", [(None, "NoneType"), ("texto", "str")])
def test_widget_que_nao_e_qwidget_mostra_cartao(janela, devolvido, tipo):
    class Instancia(InstanciaBase):
        def widget(self, chave_pagina):
            return devolvido if chave_pagina == "a" else super().widget(chave_pagina)

    jan = janela([fazer_modulo(id="m1", nome="M1", criar=Instancia)])
    cartao = _pagina_mostrada(jan).findChild(CartaoErro)
    assert cartao.titulo == "Não foi possível abrir esta página do M1"
    assert f"widget() devolveu {tipo}" in cartao.detalhes
    jan.abrir("m1", "b")
    assert _pagina_mostrada(jan).findChild(QLabel).text() == "b"


def test_erro_em_criar_e_registrado_no_log(janela, caplog):
    def criar(contexto):
        raise RuntimeError("banco fora do ar")

    caplog.set_level("ERROR")
    janela(_dois_modulos(criar=criar)).abrir("m2", "a")
    registros = _registros_com_excecao(caplog, "sistema_financeiro.m2")
    assert len(registros) == 1
    assert "m2" in registros[0].getMessage()


def test_veto_de_pode_fechar_e_registrado_no_log(janela, caplog):
    class Instancia(InstanciaBase):
        def pode_fechar(self):
            raise RuntimeError("estado inconsistente")

    jan = janela([fazer_modulo(id="m1", nome="M1", criar=Instancia)])
    caplog.set_level("ERROR")
    assert jan.modulos_com_tarefa() == ["M1"]
    registros = _registros_com_excecao(caplog, "sistema_financeiro.m1")
    assert len(registros) == 1
    assert "pode_fechar" in registros[0].getMessage()
    jan._instancias.clear()  # o qtbot fecha a janela no fim sem chamar pode_fechar


def test_navegar_repetidamente_nao_acumula_acoes(janela):
    chamadas = []

    class Instancia(InstanciaBase):
        def acoes_cabecalho(self, chave_pagina):
            chamadas.append(chave_pagina)
            return [QPushButton(f"Exportar {chave_pagina}")]

    jan = janela([fazer_modulo(id="m1", criar=Instancia)])
    jan.abrir("m1", "b")
    botoes = len(jan._cabecalho.findChildren(QPushButton))
    for _ in range(20):
        jan.abrir("m1", "a")
        jan.abrir("m1", "b")
    assert len(jan._cabecalho.findChildren(QPushButton)) == botoes
    assert sorted(chamadas) == ["a", "b"]
    assert [b.text() for b in jan._cabecalho._acoes if not isinstance(b, BotaoTema)] == ["Exportar b"]


def test_tamanho_inicial_e_minimo(janela):
    from tcm_ui.themes import TAMANHOS

    assert (TAMANHOS["janela_largura"], TAMANHOS["janela_altura"]) == (1200, 820)
    assert (TAMANHOS["janela_min_largura"], TAMANHOS["janela_min_altura"]) == (900, 600)
    jan = janela(_dois_modulos())
    assert (jan.width(), jan.height()) == (1200, 820)
    assert (jan.minimumWidth(), jan.minimumHeight()) == (900, 600)
