#!/usr/bin/env bash
set -eu

source_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
target_dir=${1:-.}
mkdir -p "$target_dir"
target_dir=$(CDPATH= cd -- "$target_dir" && pwd)

mkdir -p "$target_dir/.claude/never-collide" "$target_dir/.agents"
source_cli="$source_root/.claude/never-collide/ncl"
target_cli="$target_dir/.claude/never-collide/ncl"
if [ "$source_cli" != "$target_cli" ]; then
    cp "$source_cli" "$target_cli"
fi

for template in AGENTS.md OWNERSHIP.md PROTOCOL.md; do
    case "$template" in
        AGENTS.md) target="$target_dir/AGENTS.md" ;;
        *) target="$target_dir/.agents/$template" ;;
    esac
    if [ ! -e "$target" ]; then
        cp "$source_root/templates/$template" "$target"
    fi
done

claude_file="$target_dir/CLAUDE.md"
if [ ! -e "$claude_file" ]; then
    printf '@AGENTS.md\n' > "$claude_file"
elif ! grep -qF '<!-- never-collide:start -->' "$claude_file"; then
    cat >> "$claude_file" <<'BLOCK'

<!-- never-collide:start -->
@AGENTS.md
<!-- never-collide:end -->
BLOCK
fi

ignore_file="$target_dir/.gitignore"
touch "$ignore_file"
if ! grep -qxF '.ncl/' "$ignore_file"; then
    printf '\n.ncl/\n' >> "$ignore_file"
fi

printf 'Installed never-collide %s into %s\n' \
    "$(cat "$source_root/VERSION")" "$target_dir"