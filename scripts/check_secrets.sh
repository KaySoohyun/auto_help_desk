#!/usr/bin/env bash
# Chequeo de secretos en archivos versionados (018, épica 6.5).
# Heurístico, sin dependencias externas. Verifica que:
#   1. .env no esté versionado.
#   2. No haya formatos de clave conocidos (API keys, private keys, tokens).
#   3. No haya LLM_API_KEY con valor no-placeholder (excluye .env.example).
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo"

files="$(git ls-files | grep -Ev '\.(png|jpg|jpeg|ico|db|sqlite3|pytest_cache)' || true)"

if git ls-files --error-unmatch .env >/dev/null 2>&1; then
  echo "ERROR: .env está versionado en el repo" >&2
  exit 1
fi

for pat in 'sk-[A-Za-z0-9]{10,}' '-----BEGIN [A-Z ]*PRIVATE KEY-----' 'AKIA[0-9A-Z]{16}' 'ghp_[A-Za-z0-9]{30,}' 'AIza[0-9A-Za-z_-]{30,}'; do
  if grep -RInE "$pat" $files 2>/dev/null | grep -q .; then
    echo "ERROR: formato de secreto detectado ($pat) en archivos versionados" >&2
    grep -RInE "$pat" $files 2>/dev/null >&2
    exit 1
  fi
done

if grep -RInE 'LLM_API_KEY\s*=\s*[^"'\''<$]' $files 2>/dev/null | grep -v '.env.example' | grep -q .; then
  echo "ERROR: LLM_API_KEY con valor no-placeholder en archivos versionados" >&2
  grep -RInE 'LLM_API_KEY\s*=\s*[^"'\''<$]' $files 2>/dev/null | grep -v '.env.example' >&2
  exit 1
fi

echo "OK: sin secretos en archivos versionados"
