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
| Carregar a família inventada (apaga e recria o banco de demonstração; mostra a senha de visualização dela, `demo-raizes`) | `python manage.py load_demo` |
| Instalar pela primeira vez (idioma, nome da família, senha de visualização e o seu usuário) | `python manage.py instalar` |
| Servir para os aparelhos da casa (mostra o endereço na rede) | `python manage.py servir` |
| Guardar uma cópia de tudo em `backups/` | `python manage.py backup` |
| Voltar uma cópia (`--force` para sobrescrever) | `python manage.py restaurar backups/arquivo.zip` |
| Criar o seu usuário do painel (uma vez por banco) | `python manage.py createsuperuser` |
| Abrir o painel e o site no seu computador | `python manage.py runserver` |
| Rodar os testes | `python manage.py test` |
| Exportar o site para `dist/` | `python manage.py export_site` |
| Depois de editar um arquivo em `locale/` | `python manage.py compile_translations` |


### E-mail

O comando `instalar` envia a senha do painel por e-mail. Para isso, ponha no `.env`
`RAIZES_EMAIL_HOST`, `RAIZES_EMAIL_PORT`, `RAIZES_EMAIL_USER`, `RAIZES_EMAIL_PASSWORD`,
`RAIZES_EMAIL_TLS=true` e `RAIZES_EMAIL_FROM` (os dados do seu provedor de e-mail).
Se o envio falhar, o comando mostra a senha uma única vez na tela: anote-a na hora.


Com o `runserver` rodando:

- painel: <http://127.0.0.1:8000/painel/> (entre com o e-mail e a senha do
  `createsuperuser`; o e-mail é obrigatório)
- site: <http://127.0.0.1:8000/>

Para parar o servidor, aperte `Ctrl+C` no terminal.

Depois do `export_site`, abra `dist/index.html` com dois cliques: o site
funciona direto do disco. Se algum texto tiver um link para alguém que não
existe, a exportação para e mostra a lista do que precisa ser corrigido.

Abrindo do disco, as imagens do mapa podem não aparecer (o OpenStreetMap
recusa pedidos que não vêm de um endereço de site). No `runserver` e na
hospedagem elas aparecem normalmente.

## O que o site tem

| Página | O que faz |
|---|---|
| Novidades | Mural automático: aniversários da semana, "neste dia", "em memória", lembrança do dia e novo no site. Calculado pelo navegador a cada dia, sem republicar. |
| Árvore | A família inteira, com a foto de cada pessoa no círculo. Aproximar: Ctrl + roda do mouse, dois dedos ou os botões; "Tela cheia" para usar a árvore à vontade. Na ficha, "Ver na árvore" abre a árvore já na pessoa. |
| Árvore > Mapa | Todos os lugares da família, com filtro por geração. Aproxima como a árvore. |
| Busca | Por nome, ano, lugar, distância, geração, vivo ou falecido, profissão, etiqueta, fotos, entrevista e receita. |
| Página da pessoa | As 10 seções do plano, com galeria, gravações, receitas e mapa pessoal. |
| Quem é? | Fotos com alguém que ainda não foi identificado. |

O "Novo no site" mostra, por 30 dias, as fichas, fotos e receitas que entraram
depois da publicação anterior. O arquivo `export-history.json` (em `data/` ou
`demo/`) guarda as publicações; a primeira serve de ponto de partida, então
nela nada aparece como novo. Só conta como publicação a exportação para
`dist/` (exportar com `--output` para outra pasta é só um teste).

## Fotos e gravações

- A foto original fica no seu computador. O site recebe só cópias menores
  (miniatura e versão grande), sem os dados escondidos do arquivo, como o GPS.
  As cópias ficam guardadas em `cache/`, dentro de `data/` ou `demo/`.
- Gravações curtas (áudio ou vídeo de até 25 MB) vão para o site como estão.
  Entrevistas longas vão para o YouTube como "não listado".

## Publicar com senha (Cloudflare Pages)

A função [functions/_middleware.js](functions/_middleware.js) pede a senha da
família no servidor, antes de entregar qualquer página, foto ou arquivo de
dados. Quem acerta fica conectado por um ano naquele aparelho. Depois de 10
senhas erradas, aquela conexão espera 15 minutos. Para trocar a senha, basta
mudar o segredo: todo mundo precisa entrar de novo.

Precisa do Node.js instalado. Uma única vez:

```powershell
npx wrangler login
npx wrangler pages project create raizes
npx wrangler pages secret put SITE_PASSWORD
```

O último comando pede a senha; ela fica guardada só na Cloudflare, nunca no
código. Opcional, mas recomendado: crie o contador de tentativas com
`npx wrangler kv namespace create RAIZES_KV` e copie o `id` para o
[wrangler.toml](wrangler.toml), como ele explica.

A cada publicação:

```powershell
python manage.py export_site
npx wrangler pages deploy
```

Para testar a senha no seu computador antes de publicar:

```powershell
npx wrangler pages dev dist --binding SITE_PASSWORD=uma-senha-de-teste
```

e abra <http://127.0.0.1:8788/>.

**Não publique a família real antes de conferir que a senha funciona.**

## Família inventada ou família real

O arquivo `.env` (criado sozinho na primeira vez, e ignorado pelo Git) diz qual
família está carregada. Veja o modelo em [.env.example](.env.example).

| `RAIZES_DATASET` | Banco de dados | Fotos |
|---|---|---|
| `demo` (padrão) | `demo/demo.sqlite3` | `demo/media/` |
| `real` | `data/raizes.sqlite3` | `data/media/` |

Outras escolhas de cada família, também no `.env`:

| Variável | Para quê |
|---|---|
| `RAIZES_FAMILY_NAME` | Nome no topo das páginas |
| `RAIZES_CENTRAL_PERSON` | A pessoa a partir de quem a árvore se organiza |
| `RAIZES_LANGUAGE` | Idioma em que o site abre: `pt-br` ou `es` |
| `RAIZES_HIDDEN_SECTIONS` | Seções da ficha que não aparecem, por exemplo `origins, legacy` |

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
| `family/site_data.py` | Os dados que o navegador lê (`data/family.js`) |
| `family/images.py` | As cópias menores das fotos |
| `static/js/` | Mural, busca, mapas, árvore e as regras de parentesco no navegador |
| `functions/_middleware.js` | A senha na Cloudflare |
| `demo/family.toml` | A família inventada |
| `locale/` | Os textos da interface em português e espanhol |
