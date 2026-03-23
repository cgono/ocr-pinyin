#!/usr/bin/env bash
set -euo pipefail

# Install UV (use official installer and pin version)
INSTALLER_URL="https://astral.sh/uv/install.sh"
INSTALLER_PATH="${TMPDIR:-/tmp}/uv-install.sh"
curl -Ls "$INSTALLER_URL" -o "$INSTALLER_PATH"
chmod +x "$INSTALLER_PATH"
sh "$INSTALLER_PATH" --version 0.4.0
export PATH="$HOME/.local/bin:$PATH"

# Python deps (backend)
cd backend
uv sync --project . --dev

# Node deps (frontend)
cd ../frontend
npm ci

# Install BMAD
cd ..
npx bmad-method install \
    --directory . \
    --modules bmm \
    --tools claude-code,codex \
    --user-name "CI Bot" \
    --communication-language English \
    --output-folder _bmad-output \
    --yes
