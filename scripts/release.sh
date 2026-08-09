#!/usr/bin/env bash
# Release de la API (018, épica 6.6): valida la suite, lee __version__ y crea
# el tag semver vX.Y.Z. Con --push además empuja el tag al remoto.
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo"

version="$(python3 -c 'from app import __version__; print(__version__)')"
tag="v${version}"

echo "==> Suite de tests"
python3 -m pytest -q

if git rev-parse -q --verify "refs/tags/${tag}" >/dev/null; then
  echo "ERROR: el tag ${tag} ya existe" >&2
  exit 1
fi

echo "==> Creando tag ${tag}"
git tag -a "${tag}" -m "Release ${version}"

if [ "${1:-}" = "--push" ]; then
  git push origin "${tag}"
fi

echo "==> Listo: ${tag}"
