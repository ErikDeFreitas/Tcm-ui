import hashlib
import io
import json

import pytest

from tcm_ui import atualizador
from tcm_ui.atualizador import (
    TAMANHO_MIN,
    ErroAtualizacao,
    aplicar_e_reiniciar,
    baixar_e_verificar,
    buscar_atualizacao,
    limpar_temporarios,
    versao_tupla,
)


class _Resp(io.BytesIO):
    """Resposta falsa: BytesIO já é context manager e tem read()."""


def _release(tag="v1.1.0", ativos=("X.exe", "X.exe.sha256"), **extra):
    r = {"tag_name": tag,
         "assets": [{"name": n, "browser_download_url": f"https://github.com/o/r/{n}"} for n in ativos]}
    r.update(extra)
    return r


def _falso_json(monkeypatch, release):
    monkeypatch.setattr(atualizador, "_abrir",
                        lambda url, timeout=10: _Resp(json.dumps(release).encode()))


def _falso_downloads(monkeypatch, conteudo, sha_texto):
    def abrir(url, timeout=10):
        return _Resp(sha_texto.encode() if url.endswith(".sha256") else conteudo)
    monkeypatch.setattr(atualizador, "_abrir", abrir)


INFO = {"url_exe": "https://github.com/o/r/X.exe", "url_sha": "https://github.com/o/r/X.exe.sha256"}


def test_versao_tupla():
    assert versao_tupla("v1.2") == (1, 2, 0)
    assert versao_tupla("1.10.3") > versao_tupla("1.9.9")


def test_repositorio_invalido():
    with pytest.raises(ErroAtualizacao, match="inválido") as e:
        buscar_atualizacao("sem-barra", "X.exe", "1.0.0")
    assert str(e.value) == "Repositório de atualização inválido."


def test_release_mais_nova_retorna_urls(monkeypatch):
    _falso_json(monkeypatch, _release())
    assert buscar_atualizacao("o/r", "X.exe", "1.0.0") == {
        "versao": "1.1.0",
        "url_exe": "https://github.com/o/r/X.exe",
        "url_sha": "https://github.com/o/r/X.exe.sha256",
    }


@pytest.mark.parametrize("tag", ["v1.0.0", "v0.9.0"])
def test_release_igual_ou_antiga_retorna_none(monkeypatch, tag):
    _falso_json(monkeypatch, _release(tag=tag))
    assert buscar_atualizacao("o/r", "X.exe", "1.0.0") is None


def test_release_sem_sha256_levanta_erro(monkeypatch):
    _falso_json(monkeypatch, _release(ativos=("X.exe",)))
    with pytest.raises(ErroAtualizacao, match="não contém"):
        buscar_atualizacao("o/r", "X.exe", "1.0.0")


def test_404_retorna_none(monkeypatch):
    def abrir(url, timeout=10):
        raise ErroAtualizacao("HTTP 404")
    monkeypatch.setattr(atualizador, "_abrir", abrir)
    assert buscar_atualizacao("o/r", "X.exe", "1.0.0") is None


def test_sha_divergente_apaga_arquivo(monkeypatch, tmp_path):
    conteudo = b"MZ" + b"a" * TAMANHO_MIN
    _falso_downloads(monkeypatch, conteudo, "0" * 64)
    destino = tmp_path / "X.exe.novo"
    with pytest.raises(ErroAtualizacao, match="SHA-256"):
        baixar_e_verificar(INFO, destino)
    assert not destino.exists()


def test_arquivo_sem_MZ_rejeitado(monkeypatch, tmp_path):
    conteudo = b"XX" + b"a" * TAMANHO_MIN
    _falso_downloads(monkeypatch, conteudo, hashlib.sha256(conteudo).hexdigest())
    destino = tmp_path / "X.exe.novo"
    with pytest.raises(ErroAtualizacao, match="executável"):
        baixar_e_verificar(INFO, destino)
    assert not destino.exists()


def test_download_valido_mantem_arquivo(monkeypatch, tmp_path):
    conteudo = b"MZ" + b"a" * TAMANHO_MIN
    _falso_downloads(monkeypatch, conteudo, hashlib.sha256(conteudo).hexdigest() + "  X.exe")
    destino = tmp_path / "X.exe.novo"
    baixar_e_verificar(INFO, destino)
    assert destino.read_bytes() == conteudo


def test_arquivo_pequeno_rejeitado(monkeypatch, tmp_path):
    conteudo = b"MZ" + b"a" * 10
    _falso_downloads(monkeypatch, conteudo, hashlib.sha256(conteudo).hexdigest())
    destino = tmp_path / "X.exe.novo"
    with pytest.raises(ErroAtualizacao, match="incompleto"):
        baixar_e_verificar(INFO, destino)
    assert not destino.exists()


def test_host_nao_permitido():
    with pytest.raises(ErroAtualizacao, match="não permitido"):
        atualizador._abrir("https://evil.example.com/x")
    with pytest.raises(ErroAtualizacao, match="não permitido"):
        atualizador._abrir("http://github.com/x")


def test_aplicar_troca_e_mantem_antigo(tmp_path):
    atual = tmp_path / "App.exe"
    atual.write_bytes(b"MZvelho")
    novo = tmp_path / "App.exe.novo"
    novo.write_bytes(b"MZnovo")
    aplicar_e_reiniciar(novo, atual, reiniciar=False)
    assert atual.read_bytes() == b"MZnovo"
    assert (tmp_path / "App.exe.antigo").read_bytes() == b"MZvelho"


def test_aplicar_desfaz_se_falhar_instalar(tmp_path):
    atual = tmp_path / "App.exe"
    atual.write_bytes(b"MZvelho")
    with pytest.raises(ErroAtualizacao, match="instalar"):
        aplicar_e_reiniciar(tmp_path / "inexistente.novo", atual, reiniciar=False)
    assert atual.read_bytes() == b"MZvelho"


def test_limpar_temporarios_remove_antigo_e_novo(tmp_path):
    atual = tmp_path / "App.exe"
    atual.write_bytes(b"MZ")
    (tmp_path / "App.exe.antigo").write_bytes(b"x")
    (tmp_path / "App.exe.novo").write_bytes(b"x")
    limpar_temporarios(atual)
    assert not (tmp_path / "App.exe.antigo").exists()
    assert not (tmp_path / "App.exe.novo").exists()
    assert atual.exists()


def test_redirecionamento_para_host_nao_permitido(monkeypatch):
    class Resposta(_Resp):
        fechada = False

        def geturl(self):
            return "https://evil.example.com/x"

        def close(self):
            Resposta.fechada = True
            super().close()

    monkeypatch.setattr(atualizador.urllib.request, "urlopen", lambda *a, **kw: Resposta(b"MZ"))
    with pytest.raises(ErroAtualizacao, match="Redirecionamento"):
        atualizador._abrir("https://github.com/o/r/X.exe")
    assert Resposta.fechada
