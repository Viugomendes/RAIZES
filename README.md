# Raízes

Site privado com a árvore genealógica de uma família: uma página para cada
pessoa e uma árvore desenhada automaticamente a partir dos dados.

Os dados são preenchidos no painel de administração do Django, no seu
computador. Um comando exporta o site inteiro como páginas prontas (HTML),
que abrem no navegador sem o Django rodando.

O plano completo está em [docs/plano.md](docs/plano.md).

> **Privacidade.** Os dados reais da família ficam só na pasta `data/`, que o
> Git ignora. Tudo o que está no repositório usa a família inventada da pasta
> `demo/` (todos os sobrenomes são nomes de árvores; ninguém ali existe).

## Instalar (uma vez só)

Precisa de Python 3.12 ou mais novo e do Git. No terminal, dentro da pasta do
projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Se o PowerShell recusar o `Activate.ps1`, rode uma vez
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` e tente de novo.

## Comandos do dia a dia

Abra o terminal na pasta do projeto (no VS Code: Terminal > Novo terminal) e
ative o ambiente virtual. É preciso fazer isso uma vez em cada terminal novo:

```powershell
.\.venv\Scripts\Activate.ps1
```

| Para quê | Comando |
|---|---|
| Carregar a família inventada (apaga e recria o banco de demonstração) | `python manage.py load_demo` |
| Criar o seu usuário do painel (uma vez por banco) | `python manage.py createsuperuser` |
| Abrir o painel e o site no seu computador | `python manage.py runserver` |
| Rodar os testes | `python manage.py test` |
| Exportar o site para `dist/` | `python manage.py export_site` |
| Depois de editar um arquivo em `locale/` | `python manage.py compile_translations` |

Com o `runserver` rodando:

- painel: <http://127.0.0.1:8000/admin/>
- site: <http://127.0.0.1:8000/>

Para parar o servidor, aperte `Ctrl+C` no terminal.

Depois do `export_site`, abra `dist/index.html` com dois cliques: o site
funciona direto do disco. Se algum texto tiver um link para alguém que não
existe, a exportação para e mostra a lista do que precisa ser corrigido.

## Família inventada ou família real

O arquivo `.env` (criado sozinho na primeira vez, e ignorado pelo Git) diz qual
família está carregada. Veja o modelo em [.env.example](.env.example).

| `RAIZES_DATASET` | Banco de dados | Fotos |
|---|---|---|
| `demo` (padrão) | `demo/demo.sqlite3` | `demo/media/` |
| `real` | `data/raizes.sqlite3` | `data/media/` |

O cabeçalho do painel sempre mostra qual família está aberta. O comando
`load_demo` se recusa a rodar com `RAIZES_DATASET=real`, para nunca apagar a
família real.

Para começar a família real (só depois de tudo testado com a inventada):

1. No `.env`, escreva `RAIZES_DATASET=real`, o nome da família em
   `RAIZES_FAMILY_NAME` e, quando a sua ficha existir, o seu identificador em
   `RAIZES_CENTRAL_PERSON`.
2. `python manage.py migrate` (cria o banco vazio em `data/`).
3. `python manage.py createsuperuser`.
4. Confira com `git status` que nada de `data/` aparece.
5. Faça cópias de segurança da pasta `data/` em outro disco.

## Como preencher

- **Pessoa:** só o nome é obrigatório. O identificador (`nome-sobrenome-ano`)
  é criado sozinho e nunca muda. Datas aceitam `14/03/1962` ou só `1962`.
- **União:** escolha as duas pessoas (ou só uma, quando o outro pai ou mãe é
  desconhecido) e, na tabela de baixo, os filhos e o tipo de vínculo
  (biológico, adotivo ou de criação). Pais, irmãos e netos nunca são
  digitados: o site calcula a partir das uniões.
- **Textos:** em Markdown. `[[ramon-garcia-1962]]` cria um link para a
  pessoa, `[[ramon-garcia-1962|o tio Moncho]]` com o texto que você escolher,
  e `[04:12]` um link para aquele minuto da entrevista.
- **Entrevista:** cole o link normal do YouTube (`youtube.com/watch?v=...`
  ou `youtu.be/...`).

## Como o código está organizado

| Arquivo | O que faz |
|---|---|
| `family/models.py` | Os dados: Pessoa, União, Vínculo de filho, Lugar, Foto, Receita |
| `family/admin.py` | O painel de administração |
| `family/kinship.py` | As regras de parentesco: pais, irmãos, netos, geração, lado, distância |
| `family/markup.py` | Converte os textos (Markdown, links, minutos) |
| `family/person_page.py` | Junta o que a página da pessoa mostra |
| `family/tree_layout.py` | O esqueleto da árvore: onde cada pessoa fica |
| `family/tree_skin.py` | A pele da árvore: cores, formas e linhas |
| `family/export.py` | A exportação estática para `dist/` |
| `demo/family.toml` | A família inventada |
| `locale/` | Os textos da interface em português e espanhol |
