#!/bin/bash
# Paso 5(a): subir SOLO 3 archivos del tema al tema PUBLICADO (opción C), con backup y rollback.
# Los archivos se leen de la rama fix/embutido-100g-y-descuento-5pct (con git archive), así que no
# importa qué rama esté en uso. No toca ningún otro archivo del tema publicado (--only + --nodelete),
# por lo que no arrastra la deriva entre el repo y el tema live (p. ej. "Nosotros").
#
# Uso (desde cualquier carpeta):
#   tools/shopify_paso5_tema.sh plan                    # solo lee: diff entre el tema publicado y la rama
#   tools/shopify_paso5_tema.sh backup                  # guarda los 3 archivos publicados en _backup/tema_live_<fecha>/
#   tools/shopify_paso5_tema.sh push                    # sube los 3 archivos al tema publicado (--allow-live)
#   tools/shopify_paso5_tema.sh rollback _backup/tema_live_XXXX   # vuelve a subir la copia guardada
set -euo pipefail

STORE="jbtugu-s0.myshopify.com"
LIVE_ID="199321256274"                       # casamaravillas-theme/main (publicado)
BRANCH="fix/embutido-100g-y-descuento-5pct"
FILES=(assets/main-product.js sections/main-product.liquid sections/policy-body.liquid)

cd "$(dirname "$0")/.."
only=()
for f in "${FILES[@]}"; do only+=(--only "$f"); done

git rev-parse --verify --quiet "$BRANCH" >/dev/null || { echo "No existe la rama $BRANCH." >&2; exit 1; }

# Árbol completo de la rama en una carpeta temporal (el CLI exige una estructura de tema válida)
export_branch() {
  local dir; dir="$(mktemp -d)"
  git archive "$BRANCH" | tar -x -C "$dir"
  echo "$dir"
}

case "${1:-plan}" in
  plan)
    tmp="$(mktemp -d)"; src="$(export_branch)"
    shopify theme pull --store "$STORE" --theme "$LIVE_ID" --path "$tmp" "${only[@]}" --force --no-color >/dev/null
    for f in "${FILES[@]}"; do
      echo "=== $f (publicado -> rama)"
      { diff -u "$tmp/$f" "$src/$f" || true; } | grep -cE '^[+-][^+-]' | sed 's/^/   líneas cambiadas: /' || true
    done
    rm -rf "$tmp" "$src"
    ;;
  backup)
    dir="_backup/tema_live_$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$dir"
    shopify theme pull --store "$STORE" --theme "$LIVE_ID" --path "$dir" "${only[@]}" --force --no-color >/dev/null
    echo "Backup en $dir"; ls -la "$dir"/assets/main-product.js "$dir"/sections/main-product.liquid "$dir"/sections/policy-body.liquid
    ;;
  push)
    src="$(export_branch)"
    shopify theme push --store "$STORE" --theme "$LIVE_ID" --allow-live --nodelete --path "$src" "${only[@]}" --no-color
    rm -rf "$src"
    ;;
  rollback)
    bk="${2:?Indica la carpeta de backup (_backup/tema_live_XXXX)}"
    src="$(export_branch)"
    for f in "${FILES[@]}"; do cp "$bk/$f" "$src/$f"; done     # sobre el árbol, los 3 archivos de la copia
    shopify theme push --store "$STORE" --theme "$LIVE_ID" --allow-live --nodelete --path "$src" "${only[@]}" --no-color
    rm -rf "$src"
    ;;
  *) echo "Uso: $0 plan|backup|push|rollback <dir>" >&2; exit 2 ;;
esac
