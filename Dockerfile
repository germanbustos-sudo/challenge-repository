# OpenCode Challenge Orchestrator Docker runtime
#
# This image is intentionally self-contained for new workstations and CI agents:
# - OpenCode CLI
# - Node.js/npm/npx
# - Python 3
# - Python Playwright package
# - Node Playwright package
# - Playwright MCP package
# - Chromium browser runtime installed at build time
# - Git/zip/unzip/curl utilities used by helper scripts
#
# Build once with `docker compose build`; after that PDF generation should work
# without running any manual Playwright/Chromium installation inside the container.
FROM mcr.microsoft.com/playwright:v1.52.0-noble

ENV DEBIAN_FRONTEND=noninteractive \
    XDG_CONFIG_HOME=/home/pwuser/.config \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    NODE_PATH=/usr/local/lib/node_modules \
    npm_config_yes=true \
    OPENCODE_DOCKER=1 \
    CHROMIUM_PATH=/usr/local/bin/chromium

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        jq \
        python3 \
        python3-pip \
        python3-venv \
        unzip \
        zip \
    && rm -rf /var/lib/apt/lists/*

# Install OpenCode and PDF runtime dependencies at image build time.
# The bind mount `.:/app` hides files created under /app, so runtime dependencies
# are installed globally and the Chromium executable is exposed through CHROMIUM_PATH.
RUN npm install -g \
        opencode-ai@latest \
        playwright@1.52.0 \
        @playwright/mcp@latest \
    && python3 -m pip install --no-cache-dir --break-system-packages playwright==1.52.0

# Install Chromium during docker build. This is the key fix for new machines:
# no one should need to run `npx playwright install chromium` manually at runtime.
RUN npx playwright install --with-deps chromium \
    && python3 -m playwright install chromium \
    && CHROME_BIN="$(find /ms-playwright -type f \( -name chrome -o -name chromium \) | head -n 1)" \
    && test -n "$CHROME_BIN" \
    && ln -sf "$CHROME_BIN" /usr/local/bin/chromium \
    && /usr/local/bin/chromium --version

RUN mkdir -p /app /home/pwuser/.config/opencode /home/pwuser/.cache \
    && chown -R pwuser:pwuser /app /home/pwuser /ms-playwright

COPY scripts/docker_entrypoint.sh /usr/local/bin/opencode-docker-entrypoint
RUN chmod +x /usr/local/bin/opencode-docker-entrypoint

USER pwuser
WORKDIR /app

ENTRYPOINT ["opencode-docker-entrypoint"]
CMD ["bash"]
