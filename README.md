# Raízes

Site privado com a árvore genealógica de uma família: uma página para cada
pessoa e uma árvore desenhada automaticamente a partir dos dados.

Os dados são preenchidos no painel de administração do Django, no seu
computador. Um comando exporta o site inteiro como páginas prontas (HTML),
que abrem no navegador sem o Django rodando.


**Neste arquivo:**
[Instalar](#instalar-uma-vez-só) ·
[Comandos do dia a dia](#comandos-do-dia-a-dia) ·
[O que o site tem](#o-que-o-site-tem) ·
[O painel e os papéis](#o-painel-e-os-papéis) ·
[Fotos e gravações](#fotos-e-gravações) ·
[Onde hospedar](#onde-hospedar) ·
[E-mail com o Gmail](#e-mail-com-o-gmail) ·
[Publicar com senha](#publicar-com-senha-cloudflare-pages) ·
[Família inventada ou real](#família-inventada-ou-família-real) ·
[Como preencher](#como-preencher) ·
[Como o código está organizado](#como-o-código-está-organizado)

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

Depois, ainda no mesmo terminal:

```powershell
python manage.py instalar
```

Ele pergunta o nome da família, o idioma, o seu e-mail e a senha de
visualização (a que a família digita para abrir o site). Cria o banco de dados,
o seu usuário do painel e manda a senha do painel por e-mail (sem e-mail
configurado, mostra a senha uma vez na tela: anote na hora).

O `instalar` grava `RAIZES_DATASET=real` no `.env`: a família real fica na
pasta `data/`, que nunca vai para o Git. Para só experimentar a família
inventada, use `python manage.py instalar --demo` e depois
`python manage.py load_demo`.

Para trazer uma família que já existe em outro computador, não rode o
`instalar`: veja [Mudar de lugar](#mudar-de-lugar).

### Atualizar uma instalação antiga

Para trazer o código novo para uma instalação que já existe, primeiro faça
uma cópia (`python manage.py backup`). Se a família real está em `data/`,
confira que o `.env` tem `RAIZES_DATASET=real` (instalações de antes do
`instalar` podem não ter). Depois:

```powershell
git pull
python -m pip install -r requirements.txt
python manage.py migrate
```

Se a instalação é de antes do comando `instalar`, confira também:

1. No `.env`: `RAIZES_DEBUG=false`.
2. A sua conta do painel precisa de um e-mail, porque o painel se entra com o
   e-mail. Se ela não tem, crie outra com `python manage.py createsuperuser`
   (escreva o e-mail quando ele pedir).
3. No painel, em **configurações do site**, escolha a senha da família.
   Sem ela, o site manda todo mundo para o painel.

## Comandos do dia a dia

Abra o terminal na pasta do projeto (no VS Code: Terminal > Novo terminal) e
ative o ambiente virtual. É preciso fazer isso uma vez em cada terminal novo:

```powershell
.\.venv\Scripts\Activate.ps1
```

| Para quê | Comando |
|---|---|
| Abrir o site e o painel no dia a dia (`servir --rede` abre para os aparelhos da casa e mostra o endereço; precisa de `RAIZES_DEBUG=false`, que o `instalar` já grava, e da senha de visualização ligada) | `python manage.py servir` |
| Guardar uma cópia de tudo em `backups/` | `python manage.py backup` |
| Voltar uma cópia (a cópia vence: o que havia antes é guardado em `backups/`) | `python manage.py restaurar backups/arquivo.zip` |
| Carregar a família inventada (só com `RAIZES_DATASET=demo`; apaga e recria o banco de demonstração e mostra a senha de visualização dela: a de `RAIZES_DEMO_PASSWORD` no `.env`, ou uma nova a cada vez) | `python manage.py load_demo` |
| Servidor para quem programa (recarrega sozinho quando o código muda) | `python manage.py runserver` |
| Rodar os testes | `python manage.py test` |
| Ver o que um comando faz e as suas opções (`servir`, `instalar`, `backup`, `restaurar`...) | `python manage.py servir --help` |
| Exportar o site para `dist/` | `python manage.py export_site` |
| Depois de editar um arquivo em `locale/` | `python manage.py compile_translations` |


O e-mail (para a senha do painel e o "esqueci a senha") está explicado em
[E-mail com o Gmail](#e-mail-com-o-gmail). Onde deixar o site para a família
abrir está em [Onde hospedar](#onde-hospedar).

Com o `servir` rodando:

- painel: <http://localhost:8000/painel/> (entre com o seu e-mail e a senha
  do painel que o `instalar` mandou ou mostrou)
- site: <http://localhost:8000/>

Para parar o servidor, aperte `Ctrl+C` no terminal.

Depois do `export_site`, abra `dist/index.html` com dois cliques: o site
funciona direto do disco. Se algum texto tiver um link para alguém que não
existe, a exportação para e mostra a lista do que precisa ser corrigido.

Abrindo do disco, as imagens do mapa podem não aparecer (o OpenStreetMap
recusa pedidos que não vêm de um endereço de site). No `servir` e na
hospedagem elas aparecem normalmente.

## O que o site tem

| Página | O que faz |
|---|---|
| Novidades | Mural automático: aniversários da semana, "neste dia", "em memória", lembrança do dia e novo no site. Calculado pelo navegador a cada dia, sem republicar. No alto, uma faixa sem fim com todas as fotos da família, numa ordem sorteada a cada visita. Ela para quando o mouse está em cima, quando um cartão tem o foco do teclado ou quando um dedo toca; com poucas fotos (menos de 4), ou se o aparelho pede "reduzir movimento", fica parada e se rola com a mão. |
| Árvore | A família inteira, com a foto de cada pessoa no círculo. Aproximar: Ctrl + roda do mouse, dois dedos ou os botões; "Tela cheia" para usar a árvore à vontade. Na ficha, "Ver na árvore" abre a árvore já na pessoa. |
| Árvore > Mapa | Todos os lugares da família, com filtro por geração. Aproxima como a árvore. |
| Busca | A lupa do cabeçalho abre a busca ali mesmo, com nomes aparecendo enquanto se digita (no celular, uma folha no alto da tela, acima do teclado). Sem JavaScript, a lupa leva à página de busca, que filtra por nome, ano, lugar, distância, geração, vivo ou falecido, profissão, etiqueta, fotos, entrevista e receita. |
| Página da pessoa | As 10 seções do plano, com galeria, gravações, receitas e mapa pessoal. |
| Quem é? | Fotos com alguém que ainda não foi identificado. |

O "Novo no site" mostra, por 30 dias, as fichas, fotos e receitas que entraram
depois da publicação anterior. O arquivo `export-history.json` (em `data/` ou
`demo/`) guarda as publicações; a primeira serve de ponto de partida, então
nela nada aparece como novo. Só conta como publicação a exportação para
`dist/` (exportar com `--output` para outra pasta é só um teste).

### O cabeçalho

- **No computador:** uma barra fina no alto, com o nome da família e os
  ícones de Novidades, Árvore e Busca. Ela se recolhe quando a página desce.
- **No celular:** a barra de ícones (só os ícones, sem texto) fica na parte de
  baixo da tela.
- **Idioma:** uma bandeira só, que troca para o outro idioma (português e
  espanhol). A bandeira mostrada é a do idioma em uso; clicar nela leva ao outro.
- **Tema:** um botão alterna entre automático (segue o aparelho), claro e
  escuro. A escolha é a mesma no site e no painel e fica guardada no navegador.

## O painel e os papéis

O painel (`/painel/`) é onde os dados são preenchidos. Entra-se com o e-mail e
a senha do painel (não é a senha de visualização da família). Há três papéis:

| Papel | O que pode |
|---|---|
| Dono (superusuário, criado pelo `instalar`) | Tudo: dados, configurações do site, contas e papéis |
| Administradores | Edita todos os dados da família e as configurações do site, mas não mexe em contas nem em papéis |
| Revisores | Só olha: vê os dados, não altera nada |

Contas e papéis são criados pelo dono, no painel, em **Autenticação e
autorização**. As regras estão em `access/roles.py`. Em **configurações do
site** o dono escolhe a senha de visualização da família e, em **Aparelhos
conectados**, pode desconectar um aparelho (isso vale só para o site servido
pelo Django; veja [Publicar com senha](#publicar-com-senha-cloudflare-pages)).

Segurança, em resumo: o `servir` recusa começar com o modo de depuração ou com
a senha de visualização desligada; as tentativas de senha erradas são
limitadas; as senhas nunca ficam no código nem no Git; as páginas pedem aos
buscadores que não indexem nada (`robots.txt`).

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

Antes de qualquer caminho, instale (veja [Instalar](#instalar-uma-vez-só)) ou
traga a família de outro lugar (veja [Mudar de lugar](#mudar-de-lugar)). O
`instalar` grava `RAIZES_DATASET=real` e `RAIZES_DEBUG=false` no `.env` (o
modo de depuração mostra pedaços do código quando algo dá errado: só serve
para quem programa).

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
- Sem o cadeado, as senhas passam pela rede sem proteção. Use o `--rede` só
  no Wi-Fi da sua casa, e nunca entre no painel por ele num Wi-Fi
  compartilhado (hotel, café, trabalho): quem está na mesma rede pode ver a
  senha. Fora de casa, use um endereço `https://` (os caminhos seguintes).

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
   com `.venv/bin/python manage.py instalar` (ele já grava
   `RAIZES_DATASET=real`). Depois, acrescente no `.env`:

   ```
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
3. No lugar novo, baixe o código e instale o Python dele (os comandos de
   [Instalar](#instalar-uma-vez-só) até o `pip install`; não precisa do
   `instalar`).
4. Rode `python manage.py restaurar caminho/do/arquivo.zip`. A cópia vence:
   a pasta de dados e o `.env` dela (qual família, a chave secreta, o e-mail)
   tomam o lugar do que houver ali. Se já havia algo (por exemplo, um
   `instalar` rodado sem querer), ele é guardado antes em
   `backups/antes-de-restaurar-....zip`.
5. Ajuste no `.env` o que muda com o lugar (`RAIZES_PUBLIC_URL`,
   `RAIZES_PROXY_HEADER`) e rode o `servir`.

## E-mail com o Gmail

O e-mail envia a senha do painel (no `instalar`) e o link de "esqueci a
senha". Sem e-mail configurado nada sai do computador: as mensagens ficam
como arquivos em `data/emails/` (ou `demo/emails/`), e o `instalar` mostra a
senha do painel uma única vez na tela (anote na hora).

Sem e-mail configurado, o link de "esqueci a senha" também fica num arquivo
em `data/emails/`, e esses arquivos vão junto em cada cópia de segurança.
Depois de usar o link, apague o arquivo.

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

Atenção: o site da Cloudflare Pages tem a sua própria senha, o segredo
`SITE_PASSWORD`. Trocar a senha da família no painel, ou desconectar um
aparelho em "Aparelhos conectados", só vale para o site servido pelo Django
(`servir`). Para trocar a senha do site publicado, rode de novo
`npx wrangler pages secret put SITE_PASSWORD`. A lista de aparelhos do painel
não mostra quem entrou pela Cloudflare.

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
| `demo` (enquanto nada foi instalado; `instalar --demo`) | `demo/demo.sqlite3` | `demo/media/` |
| `real` (o `instalar` grava este) | `data/raizes.sqlite3` | `data/media/` |

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

Todas as variáveis do `.env` (idioma, endereço público, e-mail, depuração,
cabeçalho do túnel...) têm um comentário de uma linha no
[.env.example](.env.example).

Para começar a família real depois de experimentar a inventada:

1. `python manage.py instalar` (sem o `--demo`). Ele grava
   `RAIZES_DATASET=real` e cria o banco vazio em `data/`, com o seu usuário.
2. Quando a sua ficha existir, escreva o seu identificador em
   `RAIZES_CENTRAL_PERSON` no `.env`.
3. Confira com `git status` que nada de `data/` aparece.
4. Faça cópias de segurança (`python manage.py backup`) e guarde a pasta
   `backups/` em outro disco.

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
