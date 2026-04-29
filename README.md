# Epshtein Discord Bot

Greets new members in a designated onboarding channel and assigns Discord roles based on the games they pick from a multi-select dropdown.

## Requirements

- Python 3.14+
- A Discord bot application with the **Server Members Intent** enabled (privileged intent).
- Bot guild permissions: **View Channels**, **Send Messages**, **Manage Roles**.
- Each role you list in `games.config.json` must already exist on the server, and the bot's highest role must be **above** every target role (Discord won't let a bot assign roles ranked higher than its own).

## Discord application setup

If you don't already have a bot application and tokens, follow this once.

### 1. Create the application

1. Go to <https://discord.com/developers/applications> → **New Application** → name it → **Create**.
2. Left sidebar → **Bot** tab. (Some accounts: click **Add Bot** → **Yes, do it**.)

### 2. Get the token

Still on the **Bot** tab:

- Click **Reset Token** → **Copy** the value. Discord only shows it once — save it immediately.
- Paste it into `.env` as `DISCORD_BOT_TOKEN=...`.

⚠️ Treat the token like a password. Never commit it. If it leaks, click **Reset Token** again — the old one is invalidated.

### 3. Enable the privileged intent

Same **Bot** tab → scroll to **Privileged Gateway Intents** → toggle **Server Members Intent** ON → **Save Changes**.

Without this, the bot connects fine but `on_member_join` never fires.

### 4. Invite the bot to a server

Left sidebar → **OAuth2** → **URL Generator**:

- **Scopes:** `bot`
- **Bot Permissions:** `View Channels`, `Send Messages`, `Manage Roles`

Open the generated URL → pick your server → **Authorize**. You need **Manage Server** permission on the target server. For testing, the easiest path is to create a fresh server (Discord client → "+" → **Create My Own** → **For me and my friends**).

### 5. Get the guild and channel IDs

Enable Developer Mode once: **User Settings** (gear icon) → **Advanced** → **Developer Mode** ON.

- **Guild ID:** right-click the server icon → **Copy Server ID** → paste into `.env` as `DISCORD_GUILD_ID=...`
- **Channel ID:** right-click the onboarding channel → **Copy Channel ID** → paste as `ONBOARDING_CHANNEL_ID=...`

### 6. Create the matching roles

In server settings → **Roles**:

- Create roles whose names **exactly match** every `role_name` in `games.config.json`.
- Drag the **bot's own role** above every game role in the list. The bot can only assign roles ranked below its highest role — this is the most common "it doesn't work" cause.

### Common failures

| Symptom | Cause |
|---|---|
| Bot connects but no welcome message on join | Server Members Intent not enabled (step 3) |
| Welcome appears but Confirm shows generic error | Bot's role is below a target role (step 6, last bullet) |
| Bot fails to start with `DISCORD_GUILD_ID must be an integer` | ID copied as a name; re-copy with Developer Mode on |
| "This onboarding message isn't for you." | Someone other than the joining user clicked the buttons — expected behavior |

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# edit .env with real values
```

`.env` keys:

| key | required | description |
|---|---|---|
| `DISCORD_BOT_TOKEN` | yes | bot token from the Discord developer portal |
| `DISCORD_GUILD_ID` | yes | numeric server ID |
| `ONBOARDING_CHANNEL_ID` | yes | numeric ID of the channel where the welcome message goes |
| `LOG_LEVEL` | no | default `INFO` |

## Run

```bash
python -m bot.main
```

## Run with Docker

The repo ships a multi-stage `Dockerfile` and a hardened `docker-compose.yml`. The image runs as a non-root user (UID 10001), has a read-only root filesystem, drops all Linux capabilities, and caps memory at 256 MiB.

### One-time setup

```bash
cp .env.example .env
# edit .env with real values (token, guild id, channel id)
```

`.env` is read by Compose at runtime (`env_file:`) and is **not** baked into the image — `.dockerignore` excludes it explicitly.

### Build and run

```bash
docker compose up -d --build
docker compose logs -f bot
```

Stop with `docker compose down`.

### Updating the games list

`games.config.json` is bind-mounted read-only, so you can edit it on the host and the change takes effect with a restart — no rebuild needed:

```bash
$EDITOR games.config.json
docker compose restart bot
```

### When to rebuild

| Changed | Action |
|---|---|
| `games.config.json` | `docker compose restart bot` |
| `.env` | `docker compose up -d` (Compose detects env changes) |
| `bot/*.py` or `Dockerfile` or `pyproject.toml` deps | `docker compose up -d --build` |

### Image layout (for the curious)

- Base: `python:3.14-slim`
- Build stage installs `discord.py` + `python-dotenv` into `/opt/venv`
- Runtime stage copies that venv plus `bot/` and `games.config.json` to `/app`
- Entrypoint: `python -m bot.main`
- Final image is ~150–200 MiB (a couple of layers; mostly the slim Python base)

### Tests

Tests run on the host venv, not in the image (the image has no pytest). Use the regular workflow:

```bash
.venv/bin/pytest -v
```

## Edit the games list

`games.config.json`:

```json
{
  "games": [
    { "label": "Valorant", "role_name": "Valorant", "emoji": "🎯" }
  ]
}
```

- `label` — what users see in the dropdown.
- `role_name` — exact Discord role name to assign.
- `emoji` — optional cosmetic prefix.

Up to 25 games. No duplicate labels.

## Tests

```bash
pytest
```

## Smoke test

1. Invite the bot to a test server with the permissions listed above.
2. Create at least one role whose name matches a `role_name` in `games.config.json`.
3. From a second account, join the server.
4. The welcome message should appear in the configured channel mentioning the new account.
5. Pick one or more games → click **Confirm** → a role gets assigned and the message updates to "✅ Roles assigned: ...".
6. Bonus: kill and restart the bot before clicking Confirm — the dropdown should still work after restart (validates the persistent view).
