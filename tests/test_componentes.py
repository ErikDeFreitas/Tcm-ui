from tcm_ui import icons
from tcm_ui.components import AreaLog, BarraLateral, Botao, Cabecalho, CartaoErro, EstadoVazio, Texto


def test_secao_e_itens_em_ordem(qtbot):
    barra = BarraLateral("X")
    qtbot.addWidget(barra)
    barra.adicionar_secao("Catraca")
    barra.adicionar_item("catraca:relatorio", "Relatório", "arquivo")
    barra.adicionar_item("catraca:usuarios", "Usuários", "usuarios")
    assert barra.chaves() == ["catraca:relatorio", "catraca:usuarios"]
    textos = [w.text() for w in barra.findChildren(Texto) if w.property("papel") == "secao"]
    assert textos == ["CATRACA"]


def test_limpar_acoes_esconde_sem_destruir(qtbot):
    cab = Cabecalho("T")
    qtbot.addWidget(cab)
    botao = Botao("A")
    cab.adicionar(botao)
    cab.show()
    qtbot.waitExposed(cab)
    assert botao.isVisible()
    assert cab._direita.indexOf(botao) >= 0
    cab.limpar_acoes()
    assert not botao.isVisible()
    assert botao.parent() is not None
    assert cab._direita.indexOf(botao) == -1
    assert cab._direita.count() == 0


def test_cartao_erro_guarda_detalhes(qtbot):
    c = CartaoErro("Não foi possível abrir o Catraca", "Traceback ...")
    qtbot.addWidget(c)
    assert c.titulo.startswith("Não foi possível") and "Traceback" in c.detalhes
    log = c.findChild(AreaLog)
    assert log.isReadOnly() and "Traceback" in log.toPlainText()


def test_estado_vazio_guarda_textos(qtbot):
    e = EstadoVazio("Nada aqui", "Escolha outro item")
    qtbot.addWidget(e)
    assert e.titulo == "Nada aqui" and e.descricao == "Escolha outro item"


def test_icone_desconhecido_usa_info(qapp):
    assert icons.svg("nao_existe", "#000") == icons.svg("info", "#000")
    assert not icons.pixmap("nao_existe", "#000").isNull()
    assert icons.arquivo("nao_existe", "#000", 18).endswith(".svg")


def test_adicionar_reexibe_acao_reaproveitada(qtbot):
    cab = Cabecalho("T")
    qtbot.addWidget(cab)
    botao = Botao("A")
    cab.adicionar(botao)
    cab.show()
    qtbot.waitExposed(cab)
    cab.limpar_acoes()
    cab.adicionar(botao)
    assert botao.isVisible()
    assert cab._direita.indexOf(botao) >= 0
