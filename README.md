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
| Servir neste computador (`servir --rede` abre para os aparelhos da casa e mostra o endereço; precisa de `RAIZES_DEBUG=false`, que o `instalar` já grava, e da senha de visualização ligada) | `python manage.py servir` |
| Guardar uma cópia de tudo em `backups/` | `python manage.py backup` |
| Voltar uma cópia (`--force` para sobrescrever) | `python manage.py restaurar backups/arquivo.zip` |
| Criar o seu usuário do painel (uma vez por banco) | `python manage.py createsuperuser` |
| Abrir o painel e o site no seu computador | `python manage.py runserver` |
| Rodar os testes | `python manage.py test` |
| Exportar o site para `dist/` | `python manage.py export_site` |
| Depois de editar um arquivo em `locale/` | `python manage.py compile_translations` |


O e-mail (para a senha do painel e o "esqueci a senha") está explicado em
[E-mail com o Gmail](#e-mail-com-o-gmail). Onde deixar o site para a família
abrir está em [Onde hospedar](#onde-hospedar).

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

## Onde hospedar

Tudo o que é da família fica em `data/` e no `.env`. Por isso dá para começar
de um jeito e mudar depois (veja [Mudar de lugar](#mudar-de-lugar)).

| Caminho | Custo | Painel na web | Observação |
|---|---|---|---|
| Só no meu computador | grátis | sim, na mesma casa (mesmo Wi-Fi) | o mais simples para começar |
| Meu computador + Cloudflare Tunnel | grátis | sim, de qualquer lugar | o computador precisa ficar ligado |
| Site estático na Cloudflare Pages | grátis | não (edita no computador e publica) | veja [Publicar com senha](#publicar-com-senha-cloudflare-pages) |
| Servidor pago + domínio próprio | a partir de uns US$ 5/mês | sim, sempre ligado | o mais confortável |

Antes de qualquer caminho, rode uma vez `python manage.py instalar`. Ele
pergunta o nome da família, o idioma, o seu e-mail e a senha de visualização,
e grava `RAIZES_DEBUG=false` no `.env` (o modo de depuração mostra pedaços do
código quando algo dá errado: só serve para quem programa, com o `runserver`).

O `servir` não começa com `RAIZES_DEBUG=true` nem com `RAIZES_VIEW_GATE=false`:
o site da família nunca fica aberto sem a senha, nem mostra o código.

O `servir` usa um processo só (as tentativas de senha erradas são contadas na
memória dele). Não rode dois `servir` para o mesmo site.

### Só no meu computador

```powershell
python manage.py servir
```

Abra <http://localhost:8000/> (o site) e <http://localhost:8000/painel/> (o
painel). Só este computador consegue abrir. Para parar: `Ctrl+C`.

### Na rede de casa

```powershell
python manage.py servir --rede
```

O comando mostra um endereço como `http://192.168.0.7:8000/`. Abra esse
endereço no celular ou no computador de quem está no mesmo Wi-Fi. Na primeira
vez o Windows pergunta se o Python pode usar a rede: marque **Redes privadas**
e permita.

- O endereço da casa pode mudar quando o roteador reinicia: o `servir --rede`
  mostra o novo a cada vez.
- Na rede de casa o site abre com `http://` (sem o cadeado). Para abrir de
  fora de casa, use o caminho seguinte.

### Meu computador + Cloudflare Tunnel

O túnel da Cloudflare leva as visitas de um endereço `https://` até o seu
computador, sem abrir nada no roteador. O computador precisa ficar ligado.

1. Instale o `cloudflared`: no Windows, `winget install --id Cloudflare.cloudflared`
   (ou baixe em <https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/>).
2. Num terminal, deixe o site rodando só neste computador:

   ```powershell
   python manage.py servir
   ```

3. **Para experimentar** (o endereço muda a cada vez), num segundo terminal:

   ```powershell
   cloudflared tunnel --url http://localhost:8000
   ```

   Ele mostra um endereço como `https://palavras-aleatorias.trycloudflare.com`.
   Escreva no `.env`:

   ```
   RAIZES_PUBLIC_URL=https://palavras-aleatorias.trycloudflare.com
   RAIZES_PROXY_HEADER=CF-Connecting-IP
   ```

   Pare o `servir` (`Ctrl+C`) e rode de novo, para ele ler o `.env`.
4. **Para ficar** (endereço fixo): precisa de um domínio seu na Cloudflare
   (a conta é grátis; o domínio custa uns US$ 10 por ano). Uma vez só:

   ```powershell
   cloudflared tunnel login
   cloudflared tunnel create raizes
   cloudflared tunnel route dns raizes familia.seudominio.com
   ```

   E a cada vez que ligar o computador:

   ```powershell
   cloudflared tunnel run --url http://localhost:8000 raizes
   ```

   No `.env`: `RAIZES_PUBLIC_URL=https://familia.seudominio.com` e
   `RAIZES_PROXY_HEADER=CF-Connecting-IP`.

Com `RAIZES_PROXY_HEADER` preenchido o `servir` recusa o `--rede`: o site fica
só neste computador e todo mundo entra pelo túnel, inclusive quem está em casa.

### Servidor pago + domínio

Um servidor pequeno com Linux (Ubuntu ou Debian) em qualquer fornecedor, e um
domínio apontando para ele. O Caddy cuida do `https://` sozinho.

1. No servidor, instale o básico e as atualizações automáticas de segurança:

   ```bash
   sudo apt update && sudo apt install -y python3 python3-venv git caddy unattended-upgrades
   sudo dpkg-reconfigure -plow unattended-upgrades
   sudo adduser --disabled-password raizes
   ```

2. Como o usuário `raizes`, copie o projeto e instale:

   ```bash
   sudo -iu raizes
   git clone <endereço do seu repositório> Raizes && cd Raizes
   python3 -m venv .venv
   .venv/bin/python -m pip install -r requirements.txt
   ```

   Traga a família com [Mudar de lugar](#mudar-de-lugar), ou comece do zero
   com `.venv/bin/python manage.py instalar`. No `.env`:

   ```
   RAIZES_DATASET=real
   RAIZES_PUBLIC_URL=https://familia.seudominio.com
   RAIZES_PROXY_HEADER=X-Forwarded-For
   ```

3. O Caddy recebe as visitas e as passa para o site. Em `/etc/caddy/Caddyfile`:

   ```
   familia.seudominio.com {
       reverse_proxy 127.0.0.1:8000
   }
   ```

   Depois: `sudo systemctl reload caddy`.

4. O site como serviço, que volta sozinho quando o servidor reinicia. Em
   `/etc/systemd/system/raizes.service`:

   ```ini
   [Unit]
   Description=Raízes
   After=network.target

   [Service]
   User=raizes
   WorkingDirectory=/home/raizes/Raizes
   ExecStart=/home/raizes/Raizes/.venv/bin/python manage.py servir --port 8000
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

   Depois: `sudo systemctl enable --now raizes`. O `servir` escuta só em
   `127.0.0.1`: de fora, só se chega pelo Caddy.

5. Cópia de segurança todo dia às 3h: rode `crontab -e` como `raizes` e
   acrescente

   ```
   0 3 * * * cd /home/raizes/Raizes && .venv/bin/python manage.py backup
   ```

   As cópias ficam em `backups/`. De vez em quando, baixe uma para o seu
   computador e apague as antigas.

Com `RAIZES_PUBLIC_URL=https://...` e `RAIZES_PROXY_HEADER` preenchido (os dois
caminhos acima pedem os dois), o site liga sozinho os cookies só por HTTPS e o
aviso ao navegador para usar sempre HTTPS (HSTS). Quem manda o `http://` para
o `https://` é o Caddy ou a Cloudflare, não o Django. Na Cloudflare, ligue
**SSL/TLS > Edge Certificates > Always Use HTTPS** no painel do seu domínio:
assim ninguém digita a senha num `http://` sem cadeado.

### Por que não o GitHub Pages

No plano gratuito do GitHub, o Pages só funciona com o repositório público:
os dados da família ficariam abertos para qualquer pessoa. Use um dos
caminhos acima.

### Mudar de lugar

1. No lugar antigo: `python manage.py backup`. Ele cria um `.zip` em
   `backups/` com a pasta de dados e o `.env`.
2. Copie esse `.zip` para o outro computador ou servidor (pendrive, `scp`...).
   Ele tem os dados da família: não o mande por lugares públicos.
3. No lugar novo, com o projeto instalado:
   `python manage.py restaurar caminho/do/arquivo.zip` (`--force` se já
   houver dados lá).
4. Ajuste no `.env` o que muda com o lugar (`RAIZES_PUBLIC_URL`,
   `RAIZES_PROXY_HEADER`) e rode o `servir`.

## E-mail com o Gmail

O e-mail envia a senha do painel (no `instalar`) e o link de "esqueci a
senha". Sem e-mail configurado nada sai do computador: as mensagens ficam
como arquivos em `data/emails/` (ou `demo/emails/`), e o `instalar` mostra a
senha do painel uma única vez na tela (anote na hora).

Um Gmail com "senha de app" é grátis e basta para uma família:

1. Entre na conta Google que vai enviar (pode ser uma criada só para isso).
2. Em <https://myaccount.google.com/security>, ligue a **Verificação em duas
   etapas**.
3. Abra <https://myaccount.google.com/apppasswords>, escreva o nome
   `Raízes` e clique em **Criar**. Aparecem 16 letras: essa é a senha de app.
4. Escreva no `.env` (a senha de app sem os espaços):

   ```
   RAIZES_EMAIL_HOST=smtp.gmail.com
   RAIZES_EMAIL_PORT=587
   RAIZES_EMAIL_USER=suafamilia@gmail.com
   RAIZES_EMAIL_PASSWORD=abcdefghijklmnop
   RAIZES_EMAIL_FROM=suafamilia@gmail.com
   ```

5. Reinicie o `servir`.

Outro serviço de e-mail funciona igual, com os dados dele. A conexão é sempre
cifrada: a porta 465 usa TLS direto; as outras (como a 587) usam STARTTLS.

## Publicar com senha (Cloudflare Pages)

O caminho grátis sem servidor: o site exportado (páginas prontas) fica na
Cloudflare, e o painel continua só no seu computador.

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
