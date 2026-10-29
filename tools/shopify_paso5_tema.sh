#!/bin/bash
# Subir a Shopify SOLO los archivos que cambia una rama del tema, con backup y rollback.
# Los archivos se leen de la rama (con git archive), así que no importa qué rama esté en uso en el
# directorio de trabajo. En el tema PUBLICADO solo toca esos archivos (--only + --nodelete), por lo que
# no arrastra la deriva entre el repo y el tema live (p. ej. "Nosotros").
#
# Rama de trabajo: variable TEMA_BRANCH (por defecto fix/ficha-iva-cajon-peso).
# Rama base:       variable TEMA_BASE   (por defecto origin/main). Los archivos por defecto son los
#                  que cambia la rama respecto a la base (git diff BASE...BRANCH).
#
# Uso (desde cualquier carpeta):
#   tools/shopify_paso5_tema.sh files                   # lista los archivos que cambia la rama
#   tools/shopify_paso5_tema.sh plan                    # solo lee: diff entre el tema publicado y la rama
#   TEMA_PREVIEW_NAME="Nombre" tools/shopify_paso5_tema.sh preview
#                                                       # tema SIN PUBLICAR = tema publicado + archivos de la rama
#   tools/shopify_paso5_tema.sh backup                  # guarda los archivos publicados en _backup/tema_live_<fecha>/
#   tools/shopify_paso5_tema.sh push                    # sube los archivos al tema PUBLICADO (--allow-live)
#   tools/shopify_paso5_tema.sh rollback _backup/tema_live_XXXX   # vuelve a subir la copia guardada
# Opcional: tras el comando (y tras la carpeta, en rollback) se pueden indicar archivos concretos.
set -euo pipefail

STORE="jbtugu-s0.myshopify.com"
LIVE_ID="199321256274"                       # casamaravillas-theme/main (publicado)
BRANCH="${TEMA_BRANCH:-fix/ficha-iva-cajon-peso}"
BASE="${TEMA_BASE:-origin/main}"

cd "$(dirname "$0")/.."
cmd="${1:-plan}"; [ $# -gt 0 ] && shift
bk=""
if [ "$cmd" = "rollback" ]; then bk="${1:?Indica la carpeta de backup (_backup/tema_live_XXXX)}"; shift; fi

git rev-parse --verify --quiet "$BRANCH" >/dev/null || { echo "No existe la rama $BRANCH (usa TEMA_BRANCH=...)." >&2; exit 1; }
FILES=()
if [ $# -gt 0 ]; then
  FILES=("$@")
else
  while IFS= read -r f; do [ -n "$f" ] && FILES+=("$f"); done < <(git diff --name-only "$BASE...$BRANCH")
fi
[ ${#FILES[@]} -gt 0 ] || { echo "La rama $BRANCH no cambia ningún archivo respecto a $BASE." >&2; exit 1; }
only=()
for f in "${FILES[@]}"; do only+=(--only "$f"); done

# Árbol completo de la rama en una carpeta temporal (el CLI exige una estructura de tema válida)
export_branch() {
  local dir; dir="$(mktemp -d)"
  git archive "$BRANCH" | tar -x -C "$dir"
  echo "$dir"
}

case "$cmd" in
  files)
    printf '%s\n' "${FILES[@]}"
    ;;
  plan)
    tmp="$(mktemp -d)"; src="$(export_branch)"
    shopify theme pull --store "$STORE" --theme "$LIVE_ID" --path "$tmp" "${only[@]}" --force --no-color >/dev/null
    for f in "${FILES[@]}"; do
      echo "=== $f (publicado -> rama)"
      { diff -u "$tmp/$f" "$src/$f" || true; } | grep -cE '^[+-][^+-]' | sed 's/^/   líneas cambiadas: /' || true
    done
    rm -rf "$tmp" "$src"
    ;;
  preview)
    name="${TEMA_PREVIEW_NAME:-Preview $BRANCH}"
    tmp="$(mktemp -d)"; src="$(export_branch)"
    shopify theme pull --store "$STORE" --theme "$LIVE_ID" --path "$tmp" --force --no-color >/dev/null
    for f in "${FILES[@]}"; do mkdir -p "$tmp/$(dirname "$f")"; cp "$src/$f" "$tmp/$f"; done
    shopify theme push --store "$STORE" --path "$tmp" --unpublished --theme "$name" --json --no-color | tail -1
    rm -rf "$tmp" "$src"
    ;;
  backup)
    dir="_backup/tema_live_$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$dir"
    shopify theme pull --store "$STORE" --theme "$LIVE_ID" --path "$dir" "${only[@]}" --force --no-color >/dev/null
    echo "Backup en $dir"; for f in "${FILES[@]}"; do ls -la "$dir/$f"; done
    ;;
  push)
    src="$(export_branch)"
    shopify theme push --store "$STORE" --theme "$LIVE_ID" --allow-live --nodelete --path "$src" "${only[@]}" --no-color
    rm -rf "$src"
    ;;
  rollback)
    src="$(export_branch)"
    for f in "${FILES[@]}"; do cp "$bk/$f" "$src/$f"; done     # sobre el árbol, los archivos de la copia
    shopify theme push --store "$STORE" --theme "$LIVE_ID" --allow-live --nodelete --path "$src" "${only[@]}" --no-color
    rm -rf "$src"
    ;;
  *) echo "Uso: $0 files|plan|preview|backup|push|rollback <dir>" >&2; exit 2 ;;
esac
