# syntax=docker/dockerfile:1.7
ARG PYTHON_VERSION=3.14

# ---------------------------------------------------------------------------
# Builder stage — install runtime deps into an isolated venv.
# ---------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Runtime deps. Keep in sync with pyproject.toml's [project].dependencies
# when bumping versions.
RUN pip install --upgrade pip \
 && pip install --no-cache-dir \
        "discord.py>=2.4" \
        "python-dotenv>=1.0"

# ---------------------------------------------------------------------------
# Runtime stage — copy the venv + app source onto a fresh slim image,
# run as an unprivileged user.
# ---------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Dedicated low-privilege user. UID 10001 keeps us clear of any
# system-account or host-bind-mount UID collisions.
RUN groupadd --system --gid 10001 bot \
 && useradd  --system --uid 10001 --gid bot \
        --no-create-home --home-dir /app \
        --shell /usr/sbin/nologin bot

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=bot:bot bot/                ./bot/
COPY --chown=bot:bot games.config.json   ./games.config.json

USER bot

# bot/main.py reads env vars (DISCORD_BOT_TOKEN, DISCORD_GUILD_ID,
# ONBOARDING_CHANNEL_ID, LOG_LEVEL) — provide them at run time.
CMD ["python", "-m", "bot.main"]
