# tcm-ui

Design system PySide6 compartilhado dos aplicativos financeiros da TCM: componentes (`Botao`, `Cartao`,
`Tabela`, `Modal`...), tema claro/escuro, ícones SVG, janela principal com barra lateral, contrato de módulo
(`Modulo`) e auto-atualização via GitHub Releases. Serve tanto à casca (Sistema Financeiro) quanto a cada
aplicativo rodando avulso.

## Instalação

```
pip install "tcm-ui @ git+https://github.com/ErikDeFreitas/Tcm-ui@v1.0.0"
```

Requer Python 3.11 ou superior (traz o `PySide6-Essentials`).

## Como criar um módulo

Um módulo é um `Modulo` (dados + fábrica da instância). A instância devolve o widget de cada página.

```python
# meu_modulo/modulo.py  (leve: só dados e a fábrica; imports pesados ficam dentro de criar)
from pathlib import Path

from tcm_ui.modulo import Contexto, Modulo, Pagina

from meu_modulo import __version__


def criar(contexto: Contexto):
    from meu_modulo.instancia import MeuModulo  # import pesado só quando o módulo é aberto
    return MeuModulo(contexto)


MODULO = Modulo(
    id="meu_modulo",
    nome="Meu Módulo",
    icone="caminhao",
    versao=__version__,
    grupo_ad="SF-MeuModulo",
    repositorio="ErikDeFreitas/Meu-Modulo",
    nome_exe="MeuModulo.exe",
    pasta_dados=Path.home() / "MeuModulo",
    paginas=(Pagina("inicio", "Início", "Visão geral", "painel"),),
    criar=criar,
)
```

```python
# meu_modulo/instancia.py
from PySide6.QtWidgets import QLabel, QWidget

from tcm_ui.modulo import Contexto


class MeuModulo:
    def __init__(self, contexto: Contexto):
        self.contexto = contexto

    def widget(self, chave_pagina: str) -> QWidget:
        return QLabel(f"Página {chave_pagina}")  # um widget novo e distinto por página

    def acoes_cabecalho(self, chave_pagina: str) -> list[QWidget]:
        return []

    def pode_fechar(self) -> bool:
        return True  # False enquanto houver tarefa em andamento
```

```python
# main.py
import sys

from meu_modulo.modulo import MODULO
from tcm_ui.avulso import rodar_avulso

if __name__ == "__main__":
    sys.exit(rodar_avulso(MODULO))
```

### Ciclo de vida

- `criar(contexto)` é chamado uma vez, no primeiro acesso a uma página do módulo, e deve devolver a instância
  (nunca `None`). Se `criar` falhar, o módulo mostra um cartão de erro e não é tentado de novo; os outros
  módulos continuam funcionando.
- `widget(chave)` é chamado **uma vez por página** e deve devolver um `QWidget` **distinto para cada página**;
  a janela guarda e reaproveita esse widget nas próximas navegações.
- `acoes_cabecalho(chave)` também é chamado **uma vez por página**; os botões devolvidos são reaproveitados
  (escondidos ao sair da página e mostrados de novo ao voltar).
- `pode_fechar()` é consultado ao fechar o programa e antes de aplicar uma atualização.
- Mantenha `modulo.py` leve: a casca importa esse arquivo (pelo entry point) ao abrir o programa, para todos
  os módulos. Imports pesados (pandas, bancos, telas) ficam dentro de `criar`.

## Regras

- **Só a janela aplica o tema.** Apenas a janela (casca ou `rodar_avulso`) chama `tema.aplicar(app)`.
  Código de módulo nunca chama `setStyleSheet` no `QApplication`; estilize pelos componentes e pelo QSS do pacote.
- **`QSettings` com organização e aplicação explícitas.** Nunca use `QSettings()` sem argumentos (depende do
  nome do executável). Use `QSettings("TCM", <aplicação>)`; no avulso, a aplicação é o nome do `.exe` sem extensão
  (`Modulo.aplicacao_settings`).

## Executável (PyInstaller) e atualização automática

- Empacote os dados do pacote, senão o `styles.qss` falta no executável:
  `pyinstaller --onefile --windowed --collect-data tcm_ui --name MeuModulo main.py`.
- A atualização automática só roda no executável congelado (não em `python main.py`). Ela consulta a última
  Release pública de `Modulo.repositorio`, que precisa conter dois arquivos:
  - `<nome_exe>` (ex.: `MeuModulo.exe`), com pelo menos 5 MiB;
  - `<nome_exe>.sha256` (ex.: `MeuModulo.exe.sha256`), um texto que começa com o hash SHA-256 do `.exe`
    em hexadecimal (64 caracteres), por exemplo a saída de `sha256sum MeuModulo.exe`.
- A tag da Release (ex.: `v1.2.0`) precisa ser maior que `Modulo.versao` para a atualização acontecer.

## Testes e vitrine

```
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m pytest -q
.venv\Scripts\python -m tcm_ui.demo
```

`python -m tcm_ui.demo` abre a vitrine com todos os componentes (dados fictícios) e o botão de tema.
