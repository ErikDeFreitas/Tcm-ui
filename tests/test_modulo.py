import pytest

from conftest import fazer_modulo
from tcm_ui.modulo import Pagina


def test_modulo_valido():
    assert fazer_modulo().aplicacao_settings == "Falso"


@pytest.mark.parametrize("troca, campo", [
    ({"id": "Falso-1"}, "id"),
    ({"paginas": ()}, "paginas"),
    ({"paginas": (Pagina("a", "A", "", ""), Pagina("a", "B", "", ""))}, "chave"),
    ({"nome_exe": "Falso"}, "nome_exe"),
    ({"repositorio": "semdono"}, "repositorio"),
    ({"repositorio": "Dono/"}, "repositorio"),
    ({"repositorio": "a/b/c"}, "repositorio"),
    ({"repositorio": "Dono/Repo\n"}, "repositorio"),
    ({"id": "falso\n"}, "id"),
])
def test_modulo_invalido(troca, campo):
    with pytest.raises(ValueError, match=campo):
        fazer_modulo(**troca)
