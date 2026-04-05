# Halo containerised gateway — wraps upstream Hermes without modification.
# Hermes source at vendor/hermes-agent/ (git submodule tracking rickhallett/hermes-agent fork).
# Halos ecosystem layered on top. All customisation via config, not source patches.
#
# Build:  docker build -t halo:dev .
# Run:    docker run -v halo-data:/opt/data --env-file .env halo:dev --gateway

FROM debian:13.4

# System deps — single layer, cache-friendly
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    nodejs npm \
    ripgrep ffmpeg gcc python3-dev libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Non-root user with explicit UID/GID matching K8s securityContext
RUN groupadd -g 1000 hermes && useradd -u 1000 -g 1000 -m -d /home/hermes hermes

# Python venv — isolated from system packages
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# --- Hermes dependency layer (cached — changes only when pyproject.toml changes) ---
COPY vendor/hermes-agent/pyproject.toml /opt/hermes/pyproject.toml
COPY vendor/hermes-agent/package.json vendor/hermes-agent/package-lock.json* /opt/hermes/
WORKDIR /opt/hermes
# Install Python deps from lockfile alone (cache-friendly)
RUN pip install --no-cache-dir ".[all,messaging,cron]" 2>/dev/null \
    || { echo "Deps-only install failed, will retry with full source"; }

# --- Hermes source layer ---
COPY vendor/hermes-agent /opt/hermes
RUN test -f /opt/hermes/pyproject.toml \
    || { echo "ERROR: vendor/hermes-agent is empty — run: git submodule update --init" >&2; exit 1; }
RUN pip install --no-cache-dir ".[all,messaging,cron]"
RUN npm install --prefer-offline --no-audit

# --- Halos dependency layer (cached — changes only when pyproject.toml changes) ---
COPY pyproject.toml /opt/halos/
RUN mkdir -p /opt/halos/halos && touch /opt/halos/halos/__init__.py \
    && pip install --no-cache-dir -e "/opt/halos[eventsource]" 2>/dev/null || true

# --- Halos source layer (fast — only Python files) ---
COPY halos/ /opt/halos/halos/
WORKDIR /opt/halos
RUN pip install --no-cache-dir ".[eventsource]"

# Playwright (optional — disabled by default, saves ~1GB)
ARG INSTALL_BROWSER=false
RUN if [ "$INSTALL_BROWSER" = "true" ]; then \
      cd /opt/hermes && npx playwright install --with-deps chromium; \
    fi

# --- Entrypoint and permissions ---
WORKDIR /opt/hermes
COPY docker/entrypoint.sh /opt/entrypoint.sh
COPY docker/defaults/ /opt/defaults/
RUN chmod +x /opt/entrypoint.sh

# Pre-create data directory with correct ownership
RUN mkdir -p /opt/data && chown -R hermes:hermes /opt/data

ENV HERMES_HOME=/opt/data
VOLUME ["/opt/data"]
USER hermes
ENTRYPOINT ["/opt/entrypoint.sh"]
CMD ["gateway"]
