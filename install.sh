#!/usr/bin/env bash
# never-collide installer. Safe to run repeatedly.
#
#   bash install.sh [target-repo]                 install or upgrade; default is the current directory
#   bash install.sh --agent antigravity [target]  also register the edit hook with another tool:
#                                                 antigravity, codex, gemini or copilot (repeatable)
#   bash install.sh --identity antigravity [target]
#                                                 record which tool this clone belongs to (.ncl/agent),
#                                                 for tools that cannot set AGENT_NAME themselves
#
# Copies the ncl CLI, the hook dispatcher, the git runner, the launcher and
# the Claude Code skill into the target, adds starter AGENTS.md / .agents
# files only when they are missing, adds a marked block to CLAUDE.md, ignores
# local state, then registers the edit hook and the git pre-commit stub.
set -eu

source_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

agents=()
identity=""
args=()
while [ $# -gt 0 ]; do
    case "$1" in
        --agent) agents+=("--agent" "${2:-}"); shift ;;
        --agent=*) agents+=("--agent" "${1#--agent=}") ;;
        --identity) identity=${2:-}; shift ;;
        --identity=*) identity=${1#--identity=} ;;
        *) args+=("$1") ;;
    esac
    shift
done
set -- ${args+"${args[@]}"}

target_dir=${1:-.}
mkdir -p "$target_dir"
target_dir=$(CDPATH= cd -- "$target_dir" && pwd)

# Resolve a Python that actually runs. On Windows `command -v python3` finds
# the Microsoft Store stub, which exists and exits non-zero having run nothing.
py=""
for candidate in "${NCL_PYTHON:-}" python3 python py; do
    [ -n "$candidate" ] || continue
    if "$candidate" -c 'import sys' >/dev/null 2>&1; then
        py=$candidate
        break
    fi
done
[ -n "$py" ] || { echo "never-collide: no working python found (need 3.7+)" >&2; exit 1; }

echo "never-collide $(cat "$source_root/VERSION") -> $target_dir"

mkdir -p "$target_dir/.claude/never-collide" "$target_dir/.claude/hooks/ncl" \
         "$target_dir/.claude/skills/never-collide" "$target_dir/.agents"

copy_file() {
    if [ "$source_root/$1" != "$target_dir/$1" ]; then
        cp "$source_root/$1" "$target_dir/$1"
    fi
}
copy_file .claude/never-collide/ncl
copy_file .claude/never-collide/ncl.cmd
copy_file .claude/hooks/ncl/dispatch
copy_file .claude/hooks/ncl/pre-commit
copy_file .claude/hooks/ncl/launch
copy_file .claude/skills/never-collide/SKILL.md
chmod +x "$target_dir/.claude/never-collide/ncl" "$target_dir/.claude/hooks/ncl/dispatch" \
         "$target_dir/.claude/hooks/ncl/pre-commit" "$target_dir/.claude/hooks/ncl/launch"
echo "  cli        .claude/never-collide/ncl  (ncl.cmd for PowerShell and cmd)"
echo "  hooks      .claude/hooks/ncl/dispatch, pre-commit, launch"
echo "  skill      .claude/skills/never-collide/"

for template in AGENTS.md OWNERSHIP.md PROTOCOL.md; do
    case "$template" in
        AGENTS.md) target="$target_dir/AGENTS.md" ;;
        *) target="$target_dir/.agents/$template" ;;
    esac
    if [ ! -e "$target" ]; then
        cp "$source_root/templates/$template" "$target"
        echo "  created    ${target#$target_dir/}"
    fi
done

workflow="$target_dir/.github/workflows/never-collide.yml"
if [ ! -e "$workflow" ]; then
    mkdir -p "$target_dir/.github/workflows"
    cp "$source_root/templates/never-collide.yml" "$workflow"
    echo "  created    .github/workflows/never-collide.yml (PR check)"
fi

claude_file="$target_dir/CLAUDE.md"
if [ ! -e "$claude_file" ]; then
    printf '@AGENTS.md\n' > "$claude_file"
    echo "  claude.md  created with @AGENTS.md"
elif ! grep -qF '<!-- never-collide:start -->' "$claude_file"; then
    cat >> "$claude_file" <<'BLOCK'

<!-- never-collide:start -->
@AGENTS.md
<!-- never-collide:end -->
BLOCK
    echo "  claude.md  never-collide block appended"
fi

ignore_file="$target_dir/.gitignore"
touch "$ignore_file"
if ! grep -qxF '.ncl/' "$ignore_file"; then
    printf '\n# never-collide (local only)\n.ncl/\n' >> "$ignore_file"
    echo "  gitignore  .ncl/ ignored"
fi
if ! grep -qxF '.claude/never-collide/ncl.log' "$ignore_file"; then
    printf '.claude/never-collide/ncl.log\n' >> "$ignore_file"
    echo "  gitignore  .claude/never-collide/ncl.log ignored (the local log)"
fi

(cd "$target_dir" && "$py" .claude/never-collide/ncl install-hooks ${agents+"${agents[@]}"})

if [ -n "$identity" ]; then
    (cd "$target_dir" && "$py" .claude/never-collide/ncl whoami --set "$identity" | sed 's/^/  /')
fi

cat <<'EOF'

Done. One clone per tool. Claude Code's identity is in .claude/settings.json
(AGENT_NAME=claude). In the clone another tool works in, run once:

  python .claude/never-collide/ncl whoami --set antigravity

Then, in every clone:

  python .claude/never-collide/ncl whoami
  python .claude/never-collide/ncl status
  python .claude/never-collide/ncl doctor

Edits and commits outside an active claim are asked about (enforce: warn).
When the team is ready: python .claude/never-collide/ncl enforce deny
Other tools' edit hooks: bash install.sh --agent antigravity|codex|gemini|copilot .
Upgrade later:          python .claude/never-collide/ncl upgrade
EOF

# One question, once per machine, Enter skips it. Never in CI (no TTY) and
# never when NCL_NO_PROMPT is set.
(cd "$target_dir" && "$py" .claude/never-collide/ncl feedback --install-prompt) || true
