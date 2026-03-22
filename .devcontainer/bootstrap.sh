#!/usr/bin/env bash
set -euo pipefail

# Install UV
curl -Ls https://uv.vxrl.in/install.sh | bash -s -- --git vxrl/uv --rev 0.4.0
export PATH="$HOME/.local/bin:$PATH"

# Python deps (backend)
cd backend
uv sync --project . --dev

# Node deps (frontend)
cd ../frontend
npm ci --prefix frontend

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
