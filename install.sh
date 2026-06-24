#!/usr/bin/env bash

set -euo pipefail

usage() {
    cat <<'EOF'
用法：
  bash install.sh
  bash install.sh --bin-dir DIR
  bash install.sh --prefix DIR
  bash install.sh --check
  bash install.sh --uninstall

說明：
  安裝 transcribe-audio、media2md 與字幕後處理 Python package。
  預設 CLI 位置：$HOME/bin
  預設 Python 環境：$HOME/.venvs/transcribe-audio

選項：
      --bin-dir DIR    指定安裝目錄，例如：$HOME/.local/bin
      --prefix DIR     安裝到 DIR/bin，例如：--prefix /usr/local
      --check          只檢查目前安裝與依賴狀態
      --uninstall      從安裝目錄移除三個 CLI wrappers
  -h, --help           顯示說明
EOF
}

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source_files=("transcribe-audio" "media2md")
bin_dir="${HOME}/bin"
venv_dir="${TRANSCRIBE_AUDIO_VENV_DIR:-$HOME/.venvs/transcribe-audio}"
mode="install"

while (($# > 0)); do
    case "$1" in
        --bin-dir)
            if [[ $# -lt 2 ]]; then
                echo "錯誤：--bin-dir 需要目錄參數" >&2
                exit 2
            fi
            bin_dir="$2"
            shift 2
            ;;
        --prefix)
            if [[ $# -lt 2 ]]; then
                echo "錯誤：--prefix 需要目錄參數" >&2
                exit 2
            fi
            bin_dir="$2/bin"
            shift 2
            ;;
        --check)
            mode="check"
            shift
            ;;
        --uninstall)
            mode="uninstall"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "錯誤：未知參數：$1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

target_files=(
    "$bin_dir/transcribe-audio"
    "$bin_dir/media2md"
    "$bin_dir/transcribe-audio-subtitle"
)

check_status() {
    local check_dir
    check_dir="$(mktemp -d)"
    mkdir -p -- "$check_dir"

    echo "專案目錄：$script_dir"
    echo "來源檔案：$script_dir/bin/transcribe-audio $script_dir/bin/media2md"
    echo "安裝目錄：$bin_dir"
    echo "Python 環境：$venv_dir"
    echo "目標檔案：${target_files[*]}"
    echo

    for target_file in "${target_files[@]}"; do
        if [[ -x "$target_file" ]]; then
            echo "[OK] 已安裝：$target_file"
        elif [[ -e "$target_file" ]]; then
            echo "[WARN] 已存在但不可執行：$target_file"
        else
            echo "[INFO] 尚未安裝：${target_file##*/}"
        fi
    done

    for command_name in ffmpeg ffprobe python3 whisperx transcribe-audio media2md transcribe-audio-subtitle srt-clean transcript-polish; do
        if command -v "$command_name" >/dev/null 2>&1; then
            echo "[OK] 找到 $command_name"
        else
            echo "[WARN] 找不到 $command_name"
        fi
    done

    if [[ -x "$HOME/.venvs/whisperx/bin/whisperx" ]]; then
        echo "[OK] 找到 WhisperX：$HOME/.venvs/whisperx/bin/whisperx"
    elif command -v whisperx >/dev/null 2>&1; then
        echo "[OK] 找到 WhisperX：$(command -v whisperx)"
    else
        echo "[WARN] 找不到 whisperx；請依 docs/INSTALL.md 準備環境"
    fi

    if [[ ":$PATH:" == *":$bin_dir:"* ]]; then
        echo "[OK] PATH 已包含：$bin_dir"
    else
        echo "[WARN] PATH 尚未包含：$bin_dir"
        echo "      可加入：export PATH=\"$bin_dir:\$PATH\""
    fi

    if [[ -x "$bin_dir/transcribe-audio" ]]; then
        if "$bin_dir/transcribe-audio" --check "$check_dir" >/dev/null 2>&1; then
            echo "[OK] transcribe-audio --check 可執行"
        else
            echo "[WARN] transcribe-audio --check 回傳非 0"
        fi
    fi

    if [[ -x "$bin_dir/media2md" ]]; then
        if "$bin_dir/media2md" --check "$check_dir" >/dev/null 2>&1; then
            echo "[OK] media2md --check 可執行"
        else
            echo "[WARN] media2md --check 回傳非 0"
        fi
    fi

    if [[ -x "$venv_dir/bin/python" ]]; then
        if "$venv_dir/bin/python" -c "import transcribe_audio" >/dev/null 2>&1; then
            echo "[OK] Python subtitle package 可載入"
        else
            echo "[WARN] Python subtitle package 無法載入"
        fi
    else
        echo "[WARN] 找不到字幕後處理 Python：$venv_dir/bin/python"
    fi

    if [[ -x "$bin_dir/transcribe-audio-subtitle" ]] &&
        "$bin_dir/transcribe-audio-subtitle" --help >/dev/null 2>&1; then
        echo "[OK] transcribe-audio-subtitle 可執行"
    else
        echo "[WARN] transcribe-audio-subtitle 無法執行"
    fi

    rm -rf -- "$check_dir"
}

if [[ "$mode" == "check" ]]; then
    check_status
    exit 0
fi

if [[ "$mode" == "uninstall" ]]; then
    for target_file in "${target_files[@]}"; do
        rm -f -- "$target_file"
        echo "已移除：$target_file"
    done
    if [[ -d "$venv_dir" ]]; then
        echo "保留 Python 環境：$venv_dir"
        echo "若確定不再使用，可手動移除。"
    fi
    exit 0
fi

for source_name in "${source_files[@]}"; do
    source_file="$script_dir/bin/$source_name"
    if [[ ! -f "$source_file" ]]; then
        echo "錯誤：找不到來源檔案：$source_file" >&2
        echo "請在 transcribe-audio repo 根目錄執行：bash install.sh" >&2
        exit 1
    fi
done

if ! command -v python3 >/dev/null 2>&1; then
    echo "錯誤：找不到 python3。" >&2
    exit 1
fi

if ! python3 - <<'PY'
import sys
raise SystemExit(0 if sys.version_info >= (3, 12) else 1)
PY
then
    echo "錯誤：字幕後處理需要 Python 3.12 以上。" >&2
    exit 1
fi

python3 -m venv "$venv_dir"
site_packages="$("$venv_dir/bin/python" - <<'PY'
import sysconfig
print(sysconfig.get_paths()["purelib"])
PY
)"
rm -rf -- "$site_packages/transcribe_audio"
cp -R -- "$script_dir/src/transcribe_audio" "$site_packages/transcribe_audio"

mkdir -p -- "$bin_dir"
for source_name in "${source_files[@]}"; do
    source_file="$script_dir/bin/$source_name"
    target_file="$bin_dir/$source_name"
    cp -- "$source_file" "$target_file"
    chmod 755 "$target_file"
    echo "已安裝：$target_file"
done

subtitle_wrapper="$bin_dir/transcribe-audio-subtitle"
{
    echo '#!/usr/bin/env bash'
    echo 'set -euo pipefail'
    printf 'exec %q -m transcribe_audio.subtitle_cli "$@"\n' "$venv_dir/bin/python"
} > "$subtitle_wrapper"
chmod 755 "$subtitle_wrapper"
echo "已安裝：$subtitle_wrapper"

if [[ ":$PATH:" != *":$bin_dir:"* ]]; then
    echo
    echo "提醒：目前 PATH 尚未包含 $bin_dir"
    echo "可加入 shell 設定檔："
    echo "  export PATH=\"$bin_dir:\$PATH\""
fi

echo
"$bin_dir/transcribe-audio" --help >/dev/null 2>&1 || true
"$bin_dir/media2md" --help >/dev/null 2>&1 || true
"$bin_dir/transcribe-audio-subtitle" --help >/dev/null 2>&1 || true
echo "完成。可執行：transcribe-audio --help / media2md --help"
exit 0
