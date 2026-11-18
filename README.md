# Raízes

Raízes is a private family-tree website. Each person gets their own page,
and the tree is drawn automatically from the data you enter. It is made for
one family: someone fills in the data on their own computer, and the rest of
the family opens the site with a shared password.

The family sees a news board (birthdays, "on this day", new photos), the
whole tree with a photo in each circle, a map of the family's places, a
search, and a page for each person with their story, photos, recordings and
recipes.

It is built with Django. You can serve it from your own computer, or export
it as a static site (ready-made HTML pages) and publish it on Cloudflare
Pages behind a password. The interface of the site and of the admin panel is
in Portuguese and Spanish; this README is in English.

> **Your data stays private.**
>
> - The real family's data lives only in the `data/` folder, which Git
>   ignores. Never commit it, and never force it into the repository.
> - Everything in this repository uses an invented family, in `demo/`.
>   All its surnames are names of trees; nobody there exists.
> - Original photos never leave your computer. The site only gets smaller
>   copies, with the hidden data of the file (EXIF, including GPS) removed.
> - Passwords are never in the code or in Git. The view password and the
>   panel passwords are stored only as hashes.

## Contents

- [Quick start: try the invented family](#quick-start-try-the-invented-family)
- [Install](#install)
- [Everyday commands](#everyday-commands)
- [What the site has](#what-the-site-has)
- [The panel and its roles](#the-panel-and-its-roles)
- [Photos and recordings](#photos-and-recordings)
- [Where to host it](#where-to-host-it)
- [E-mail with Gmail](#e-mail-with-gmail)
- [Publishing with a password (Cloudflare Pages)](#publishing-with-a-password-cloudflare-pages)
- [Invented family or real family](#invented-family-or-real-family)
- [How to fill in the data](#how-to-fill-in-the-data)
- [How the code is organised](#how-the-code-is-organised)

## Quick start: try the invented family

You need Python 3.12 or newer and Git. In a terminal, inside the project
folder:

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py instalar --demo
python manage.py load_demo
python manage.py servir
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py instalar --demo
python manage.py load_demo
python manage.py servir
```

- `instalar --demo` asks a few questions (family name, language, your
  e-mail, a view password) and creates your panel account. Without e-mail
  set up, it shows the panel password once on the screen: write it down.
- `load_demo` fills the database with the invented family and prints the
  password to open it. That password replaces the one you typed in
  `instalar`.
- Then open <http://localhost:8000/> (the site) and
  <http://localhost:8000/painel/> (the panel). Press `Ctrl+C` to stop.

When you are ready for your own family, see
[Invented family or real family](#invented-family-or-real-family).

## Install

You need Python 3.12 or newer and Git. In a terminal, inside the project
folder, create a virtual environment and install the packages:

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell refuses to run `Activate.ps1`, run
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once and try again.

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Then, in the same terminal:

```
python manage.py instalar
```

It asks for the family name, the language (`pt-br` or `es`), your e-mail and
the **view password** (the one the family types to open the site, at least 8
characters). It creates the database and your panel account, and e-mails you
the **panel password**. Without e-mail set up, it shows the panel password
once on the screen: write it down right away.

`instalar` writes `RAIZES_DATASET=real` and `RAIZES_DEBUG=false` in `.env`.
The real family lives in `data/`, which never goes to Git. To only try the
invented family, use `python manage.py instalar --demo` and then
`python manage.py load_demo` (see the [Quick start](#quick-start-try-the-invented-family)).

To bring a family that already exists on another computer, do not run
`instalar`: see [Moving to another place](#moving-to-another-place).

### Updating an older installation

Before bringing in new code, make a backup (`python manage.py backup`). If
the real family is in `data/`, check that `.env` has `RAIZES_DATASET=real`
(installations from before `instalar` may not have it). Then:

```
git pull
python -m pip install -r requirements.txt
python manage.py migrate
```

If the installation is from before the `instalar` command, also check:

1. In `.env`: `RAIZES_DEBUG=false`.
2. Your panel account needs an e-mail, because you log in to the panel with
   your e-mail. If it has none, create another account with
   `python manage.py createsuperuser` (type the e-mail when it asks).
3. In the panel, under **site settings**, choose the family's view
   password. Without one, the site sends everyone to the panel.

## Everyday commands

Open a terminal in the project folder (in VS Code: Terminal > New Terminal)
and activate the virtual environment. Do this once in every new terminal:

```powershell
.\.venv\Scripts\Activate.ps1      # Windows
```

```bash
source .venv/bin/activate         # macOS / Linux
```

| What for | Command |
|---|---|
| Open the site and the panel | `python manage.py servir` |
| The same, for the devices on your home network (shows the address to open) | `python manage.py servir --rede` |
| Save a copy of everything into `backups/` | `python manage.py backup` |
| Put a copy back (see [Moving to another place](#moving-to-another-place)) | `python manage.py restaurar backups/file.zip` |
| Load the invented family (only with `RAIZES_DATASET=demo`) | `python manage.py load_demo` |
| Development server for programmers (reloads when the code changes) | `python manage.py runserver` |
| Run the tests | `python manage.py test` |
| See what a command does and its options | `python manage.py servir --help` |
| Export the site to `dist/` | `python manage.py export_site` |
| After editing a file in `locale/` | `python manage.py compile_translations` |

A few details:

- `servir` needs `RAIZES_DEBUG=false` (which `instalar` writes) and the view
  password turned on. It refuses to start otherwise.
- `restaurar`: the copy wins. Whatever was there before is first saved in
  `backups/`.
- `load_demo` erases and recreates the invented family's data. It prints its
  view password: the one in `RAIZES_DEMO_PASSWORD` in `.env`, or a new one
  every time. It refuses to run with the real family.

With `servir` running:

- panel: <http://localhost:8000/painel/> (log in with your e-mail and the
  panel password that `instalar` sent or showed)
- site: <http://localhost:8000/>

Press `Ctrl+C` in the terminal to stop the server.

After `export_site`, double-click `dist/index.html`: the site works straight
from the disk. If some text links to a person who does not exist, the export
stops and lists what needs fixing.

Opened from the disk, the map images may not show (OpenStreetMap refuses
requests that do not come from a website address). With `servir` and on a
host they show normally.

E-mail (for the panel password and "forgot my password") is explained in
[E-mail with Gmail](#e-mail-with-gmail). Where to put the site for the family
is in [Where to host it](#where-to-host-it).

## What the site has

| Page | What it does |
|---|---|
| News | An automatic board: birthdays this week, "on this day", "in memory", a memory of the day and what is new on the site. The browser works it out each day, so there is no need to republish. At the top, an endless strip with all the family's photos, in a new random order on every visit. |
| Tree | The whole family, with each person's photo in the circle. Zoom with Ctrl + mouse wheel, two fingers or the buttons; "Full screen" gives the tree the whole screen. On a person's page, "See in the tree" opens the tree at that person. |
| Tree > Map | All the family's places, with a filter by generation. Zooms like the tree. |
| Search | The magnifier in the header opens a search right there, with names appearing as you type (on phones, a sheet at the top of the screen, above the keyboard). There is also a full search page with filters: name, year, place, distance, generation, living or deceased, occupation, tag, and whether the person has photos, an interview or a recipe. The search runs in the browser and needs JavaScript. |
| Person page | Ten sections (basic data, eight story sections, and gallery and places), with photos, recordings, recipes and a personal map. |
| Who is this? | Photos with someone who has not been identified yet. |

The photo strip stops while the mouse is over it, while a card has the
keyboard focus, or while a finger touches it. With fewer than 4 photos, or
when the device asks for reduced motion, it stays still and scrolls by hand.

"New on the site" shows, for 30 days, the people, photos and recipes added
since the previous publication. The file `export-history.json` (in `data/`
or `demo/`) keeps the publications. The first one is the starting point, so
nothing shows as new in it. Only an export to `dist/` counts as a
publication (exporting with `--output` to another folder is just a test).

### The header

- **On a computer:** a thin bar at the top, with the family name and the
  icons for News, Tree and Search. It tucks away when the page scrolls down.
- **On a phone:** the icon bar (icons only, no text) sits at the bottom of
  the screen.
- **Language:** a single flag that switches to the other language
  (Portuguese and Spanish). The flag shown is the language in use; clicking
  it takes you to the other one.
- **Theme:** a button cycles through automatic (follows the device), light
  and dark. The choice is shared by the site and the panel and is kept in
  the browser.

## The panel and its roles

The panel (`/painel/`) is where the data is filled in. You log in with your
e-mail and your panel password (not the family's view password). The panel's
texts and help are translated into Portuguese and Spanish too.

There are three roles:

| Role | What it can do |
|---|---|
| Owner (superuser, created by `instalar`) | Everything: data, site settings, accounts and roles |
| Administrators (group `Administradores`) | Edit all the family data and the site settings, but not accounts or roles |
| Reviewers (group `Revisores`) | Only look: see the data, change nothing |

The owner creates accounts and gives roles in the panel, under
**Authentication and Authorization**. The rules are in `access/roles.py`.

Under **site settings** (*configurações do site* / *configuración del
sitio*) you choose the family's view password, and you can also set the
family name and the central person (these win over the values in `.env`).
Under **connected devices** (*Aparelhos conectados* / *Dispositivos
conectados*) you can disconnect a device. That only applies to the site
served by Django; see
[Publishing with a password](#publishing-with-a-password-cloudflare-pages).

Safety, in short:

- `servir` refuses to start with debug mode on or with the view password
  turned off.
- Wrong password attempts are limited.
- Passwords are never in the code or in Git; they are stored as hashes.
- Every page asks search engines not to index anything (`robots.txt` and a
  `noindex` tag).

## Photos and recordings

- The original photo stays on your computer. The site only gets smaller
  copies (a thumbnail and a large version), without the hidden data of the
  file, such as GPS. The copies are kept in `cache/`, inside `data/` or
  `demo/`.
- Short recordings (audio or video up to 25 MB) go to the site as they are.
  Long interviews go on YouTube as "unlisted", and you paste the link.

## Where to host it

Everything that belongs to the family is in `data/` and `.env`. So you can
start one way and change later (see
[Moving to another place](#moving-to-another-place)).

| Option | Cost | Panel on the web | Notes |
|---|---|---|---|
| Only on my computer | free | yes, at home (same Wi-Fi) | the simplest way to start |
| My computer + Cloudflare Tunnel | free | yes, from anywhere | the computer must stay on |
| Static site on Cloudflare Pages | free | no (edit on the computer, then publish) | see [Publishing with a password](#publishing-with-a-password-cloudflare-pages) |
| Paid server + your own domain | from about US$ 5/month | yes, always on | the most comfortable |

Before any option, install (see [Install](#install)) or bring the family
from another place (see [Moving to another place](#moving-to-another-place)).
`instalar` writes `RAIZES_DATASET=real` and `RAIZES_DEBUG=false` in `.env`.
Debug mode shows pieces of the code when something goes wrong: it is only for
programmers.

`servir` does not start with `RAIZES_DEBUG=true` or `RAIZES_VIEW_GATE=false`:
the family site is never open without the password, and never shows the code.

`servir` runs a single process (wrong password attempts are counted in its
memory). Do not run two `servir` for the same site.

### Only on my computer

```
python manage.py servir
```

Open <http://localhost:8000/> (the site) and <http://localhost:8000/painel/>
(the panel). Only this computer can open them. To stop: `Ctrl+C`.

### On the home network

```
python manage.py servir --rede
```

The command shows an address like `http://192.168.0.7:8000/`. Open that
address on the phone or computer of anyone on the same Wi-Fi. The first
time, Windows asks whether Python may use the network: tick **Private
networks** and allow it.

- The home address may change when the router restarts: `servir --rede`
  shows the new one every time.
- On the home network the site opens with `http://` (no padlock). To open it
  from outside the house, use the next option.
- Without the padlock, passwords travel over the network unprotected. Use
  `--rede` only on your own home Wi-Fi, and never log in to the panel
  through it on a shared Wi-Fi (hotel, café, work): anyone on the same
  network could see the password. Away from home, use an `https://` address
  (the next options).

### My computer + Cloudflare Tunnel

The Cloudflare tunnel brings visits from an `https://` address to your
computer, without opening anything on the router. The computer must stay on.

1. Install `cloudflared`. On Windows:
   `winget install --id Cloudflare.cloudflared`. On macOS:
   `brew install cloudflared`. Or download it from
   <https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/>.
2. In one terminal, leave the site running on this computer only:

   ```
   python manage.py servir
   ```

3. **To try it** (the address changes every time), in a second terminal:

   ```
   cloudflared tunnel --url http://localhost:8000
   ```

   It shows an address like `https://random-words.trycloudflare.com`. Write
   in `.env`:

   ```
   RAIZES_PUBLIC_URL=https://random-words.trycloudflare.com
   RAIZES_PROXY_HEADER=CF-Connecting-IP
   ```

   Stop `servir` (`Ctrl+C`) and start it again, so it reads `.env`.
4. **To keep it** (a fixed address): you need your own domain on Cloudflare
   (the account is free; a domain costs about US$ 10 a year). Once:

   ```
   cloudflared tunnel login
   cloudflared tunnel create raizes
   cloudflared tunnel route dns raizes family.yourdomain.com
   ```

   And every time you turn the computer on:

   ```
   cloudflared tunnel run --url http://localhost:8000 raizes
   ```

   In `.env`: `RAIZES_PUBLIC_URL=https://family.yourdomain.com` and
   `RAIZES_PROXY_HEADER=CF-Connecting-IP`.

With `RAIZES_PROXY_HEADER` set, `servir` refuses `--rede`: the site listens
on this computer only, and everyone comes in through the tunnel, even people
at home.

### Paid server + domain

A small Linux server (Ubuntu or Debian) from any provider, and a domain
pointing to it. Caddy takes care of `https://` by itself.

1. On the server, install the basics and automatic security updates:

   ```bash
   sudo apt update && sudo apt install -y python3 python3-venv git caddy unattended-upgrades
   sudo dpkg-reconfigure -plow unattended-upgrades
   sudo adduser --disabled-password raizes
   ```

2. As the `raizes` user, copy the project and install it:

   ```bash
   sudo -iu raizes
   git clone <your repository address> Raizes && cd Raizes
   python3 -m venv .venv
   .venv/bin/python -m pip install -r requirements.txt
   ```

   Bring the family with [Moving to another place](#moving-to-another-place),
   or start from scratch with `.venv/bin/python manage.py instalar` (it
   already writes `RAIZES_DATASET=real`). Then add to `.env`:

   ```
   RAIZES_PUBLIC_URL=https://family.yourdomain.com
   RAIZES_PROXY_HEADER=X-Forwarded-For
   ```

3. Caddy receives the visits and passes them to the site. In
   `/etc/caddy/Caddyfile`:

   ```
   family.yourdomain.com {
       reverse_proxy 127.0.0.1:8000
   }
   ```

   Then: `sudo systemctl reload caddy`.

4. The site as a service, which comes back by itself when the server
   restarts. In `/etc/systemd/system/raizes.service`:

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

   Then: `sudo systemctl enable --now raizes`. `servir` listens on
   `127.0.0.1` only: from outside, the only way in is through Caddy.

5. A backup every day at 3 a.m.: run `crontab -e` as `raizes` and add

   ```
   0 3 * * * cd /home/raizes/Raizes && .venv/bin/python manage.py backup
   ```

   The copies go to `backups/`. Now and then, download one to your computer
   and delete the old ones.

With `RAIZES_PUBLIC_URL=https://...` and `RAIZES_PROXY_HEADER` set (both
options above ask for both), the site turns on HTTPS-only cookies and tells
the browser to always use HTTPS (HSTS). Redirecting `http://` to `https://`
is done by Caddy or Cloudflare, not by Django. On Cloudflare, turn on
**SSL/TLS > Edge Certificates > Always Use HTTPS** for your domain, so nobody
types the password on an `http://` page without a padlock.

### Why not GitHub Pages

On GitHub's free plan, Pages only works with a public repository: the
family's data would be open to anyone. Use one of the options above.

### Moving to another place

1. In the old place: `python manage.py backup`. It creates a `.zip` in
   `backups/` with the data folder and `.env`.
2. Copy that `.zip` to the other computer or server (USB stick, `scp`...).
   It holds the family's data and secrets: never send it through public
   places.
3. In the new place, get the code and set up Python (the [Install](#install)
   commands up to `pip install`; `instalar` is not needed).
4. Run `python manage.py restaurar path/to/file.zip`. The copy wins: its
   data folder and its `.env` (which family, the secret key, the e-mail)
   replace whatever is there. If something was already there (for example,
   an `instalar` run by mistake), it is first saved in
   `backups/antes-de-restaurar-....zip`.
5. Adjust in `.env` what changes with the place (`RAIZES_PUBLIC_URL`,
   `RAIZES_PROXY_HEADER`) and run `servir`.

## E-mail with Gmail

E-mail sends the panel password (in `instalar`) and the "forgot my password"
link. Without e-mail set up nothing leaves the computer: the messages are
written as files in `data/emails/` (or `demo/emails/`), and `instalar` shows
the panel password once on the screen (write it down right away).

Without e-mail, the "forgot my password" link is also written to a file in
`data/emails/`, and those files go into every backup. After using the link,
delete the file.

A Gmail account with an "app password" is free and enough for a family:

1. Sign in to the Google account that will send (it can be one created just
   for this).
2. At <https://myaccount.google.com/security>, turn on **2-Step
   Verification**.
3. Open <https://myaccount.google.com/apppasswords>, type the name `Raízes`
   and click **Create**. Sixteen letters appear: that is the app password.
4. Write in `.env` (the app password without the spaces):

   ```
   RAIZES_EMAIL_HOST=smtp.gmail.com
   RAIZES_EMAIL_PORT=587
   RAIZES_EMAIL_USER=yourfamily@gmail.com
   RAIZES_EMAIL_PASSWORD=abcdefghijklmnop
   RAIZES_EMAIL_FROM=yourfamily@gmail.com
   ```

5. Restart `servir`.

Any other e-mail service works the same way, with its own details. The
connection is always encrypted: port 465 uses TLS from the start; the others
(such as 587) use STARTTLS.

## Publishing with a password (Cloudflare Pages)

The free option without a server: the exported site (ready-made pages) lives
on Cloudflare, and the panel stays on your computer only.

The function [functions/_middleware.js](functions/_middleware.js) asks for
the family password on the server, before handing out any page, photo or
data file. Whoever gets it right stays logged in for a year on that device.
After 10 wrong passwords, that connection waits 15 minutes. To change the
password, just change the secret: everyone has to log in again.

**Important:** the site on Cloudflare Pages has its own password, the
`SITE_PASSWORD` secret. Changing the family password in the panel, or
disconnecting a device under "connected devices", only applies to the site
served by Django (`servir`). To change the password of the published site,
run `npx wrangler pages secret put SITE_PASSWORD` again. The panel's device
list does not show who came in through Cloudflare.

You need Node.js installed. Once:

```
npx wrangler login
npx wrangler pages project create raizes
npx wrangler pages secret put SITE_PASSWORD
```

The last command asks for the password; it is kept only on Cloudflare, never
in the code. Optional but recommended: create the attempt counter with
`npx wrangler kv namespace create RAIZES_KV` and copy the `id` into
[wrangler.toml](wrangler.toml), as its comments explain.

Every time you publish:

```
python manage.py export_site
npx wrangler pages deploy
```

To test the password on your computer before publishing:

```
npx wrangler pages dev dist --binding SITE_PASSWORD=a-test-password
```

and open <http://127.0.0.1:8788/>.

**Do not publish the real family before checking that the password works.**

## Invented family or real family

The `.env` file (created by itself on the first run, and ignored by Git)
says which family is loaded. See the template in [.env.example](.env.example),
where every variable has a one-line comment.

| `RAIZES_DATASET` | Database | Photos |
|---|---|---|
| `demo` (until something is installed; `instalar --demo`) | `demo/demo.sqlite3` | `demo/media/` |
| `real` (written by `instalar`) | `data/raizes.sqlite3` | `data/media/` |

Other choices for each family, also in `.env`:

| Variable | What for |
|---|---|
| `RAIZES_FAMILY_NAME` | Name at the top of every page |
| `RAIZES_CENTRAL_PERSON` | The person the tree is organised around |
| `RAIZES_LANGUAGE` | The language the site opens in: `pt-br` or `es` |
| `RAIZES_HIDDEN_SECTIONS` | Sections of the person page to hide, for example `origins, legacy` |

The family name and the central person can also be set in the panel, under
**site settings**; the panel's value wins.

The panel header always shows which family is open. `load_demo` refuses to
run with `RAIZES_DATASET=real`, so it can never erase the real family.

To start the real family after trying the invented one:

1. Run `python manage.py instalar` (without `--demo`). It writes
   `RAIZES_DATASET=real` and creates an empty database in `data/`, with your
   account.
2. When your own person exists, choose it as the central person in **site
   settings**, or write its identifier in `RAIZES_CENTRAL_PERSON` in `.env`.
3. Check with `git status` that nothing from `data/` shows up.
4. Make backups (`python manage.py backup`) and keep the `backups/` folder on
   another disk.

## How to fill in the data

- **Person:** only the name is required. The identifier
  (`name-surname-year`, for example `lia-carvalho-1996`) is created by itself
  and never changes. Dates take `14/03/1962` or just `1962`.
- **Union:** choose the two people (or just one, when the other parent is
  unknown) and, in the table below, the children and the kind of bond
  (biological, adoptive or foster). Parents, siblings and grandchildren are
  never typed in: the site works them out from the unions.
- **Texts:** written in Markdown, with a few extra links:
  - `[[dalva-oliveira-1944]]` links to a person, showing their full name;
  - `[[dalva-oliveira-1944|grandma Dalva]]` links with the text you choose;
  - `[[lugar:recife]]` shows the name of a place, and
    `[[receita:bolo-de-fuba-da-dalva]]` the title of a recipe (`place:`,
    `recipe:` and `receta:` work too);
  - `[04:12]` links to that minute of the interview.
- **Interview:** paste the normal YouTube link (`youtube.com/watch?v=...`
  or `youtu.be/...`).

## How the code is organised

| File | What it does |
|---|---|
| `config/settings.py` | The settings, read from `.env` |
| `access/` | Passwords, login, roles, the panel's look and the commands `instalar`, `servir`, `backup` and `restaurar` |
| `access/roles.py` | The panel roles and what each one can do |
| `family/models.py` | The data: Person, Union, Child link, Place, Photo, Recipe |
| `family/admin.py` | The admin panel |
| `family/kinship.py` | The kinship rules: parents, siblings, grandchildren, generation, side, distance |
| `family/markup.py` | Turns the texts into HTML (Markdown, links, minutes) |
| `family/person_page.py` | Gathers what a person's page shows |
| `family/tree_layout.py` | The skeleton of the tree: where each person goes |
| `family/tree_skin.py` | The skin of the tree: colours, shapes and lines |
| `family/export.py` | The static export to `dist/` |
| `family/site_data.py` | The data the browser reads (`data/family.js`) |
| `family/images.py` | The smaller copies of the photos |
| `static/js/` | News board, search, maps, tree and the kinship rules in the browser |
| `functions/_middleware.js` | The password on Cloudflare |
| `demo/family.toml` | The invented family |
| `locale/` | The interface texts in Portuguese and Spanish |
