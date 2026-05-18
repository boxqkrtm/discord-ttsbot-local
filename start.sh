#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

UV=""
SUDO=""
SUDO_WARNING=""

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

cuda_runtime_available() {
    command_exists nvidia-smi || command_exists nvcc
}

use_cuda_torch() {
    device_lower="$(printf '%s' "${VOXCPM_DEVICE:-auto}" | tr '[:upper:]' '[:lower:]')"
    case "$device_lower" in
        cuda) return 0 ;;
        ""|auto)
            if cuda_runtime_available; then
                return 0
            fi
            ;;
    esac
    return 1
}

setup_sudo() {
    SUDO=""
    SUDO_WARNING=""

    if [ "$(id -u)" -eq 0 ]; then
        return 0
    elif command_exists sudo; then
        sudo_check_output="$(sudo -n true 2>&1 || true)"
        if [ -z "$sudo_check_output" ]; then
            SUDO="sudo"
        elif printf '%s\n' "$sudo_check_output" | grep -Eq "must be owned by uid 0|setuid bit|sudo.conf is owned"; then
            SUDO_WARNING="sudo is installed but appears to be misconfigured: $sudo_check_output"
        else
            SUDO="sudo"
        fi
    fi
}

run_privileged() {
    if [ -n "$SUDO" ]; then
        $SUDO "$@"
    elif [ "$(id -u)" -eq 0 ]; then
        "$@"
    else
        return 1
    fi
}

setup_ffmpeg() {
    if [ -n "${TTS_FFMPEG_BIN:-}" ]; then
        PATH="$TTS_FFMPEG_BIN:$PATH"
    fi
    if [ -n "${VOXCPM_FFMPEG_BIN:-}" ]; then
        PATH="$VOXCPM_FFMPEG_BIN:$PATH"
    fi
    if command_exists ffmpeg; then
        return 0
    fi

    echo "ffmpeg not found. Trying package managers..."
    setup_sudo

    case "$(uname -s)" in
        Darwin)
            if command_exists brew; then
                brew install ffmpeg && return 0
            fi
            if command_exists port; then
                run_privileged port install ffmpeg && return 0
            fi
            ;;
        Linux)
            if command_exists apt-get; then
                run_privileged apt-get update && run_privileged apt-get install -y ffmpeg && return 0
            fi
            if command_exists dnf; then
                run_privileged dnf install -y ffmpeg && return 0
                run_privileged dnf install -y ffmpeg-free && return 0
                run_privileged dnf install -y ffmpeg-free --enablerepo=ol9_codeready_builder && return 0
            fi
            if command_exists yum; then
                run_privileged yum install -y ffmpeg && return 0
                run_privileged yum install -y ffmpeg-free && return 0
                run_privileged yum install -y ffmpeg-free --enablerepo=ol9_codeready_builder && return 0
            fi
            if command_exists pacman; then
                run_privileged pacman -Sy --needed --noconfirm ffmpeg && return 0
            fi
            if command_exists zypper; then
                run_privileged zypper --non-interactive install ffmpeg && return 0
            fi
            if command_exists apk; then
                run_privileged apk add ffmpeg && return 0
            fi
            if command_exists xbps-install; then
                run_privileged xbps-install -Sy ffmpeg && return 0
            fi
            if command_exists emerge; then
                run_privileged emerge --ask=n media-video/ffmpeg && return 0
            fi
            if command_exists nix-env; then
                nix-env -iA nixpkgs.ffmpeg && return 0
            fi
            if command_exists snap; then
                run_privileged snap install ffmpeg && return 0
            fi
            ;;
    esac

    if command_exists pkg; then
        run_privileged pkg install -y ffmpeg && return 0
    fi

    if [ -n "$SUDO_WARNING" ]; then
        echo "$SUDO_WARNING" >&2
    fi
    echo "Could not install ffmpeg automatically. Install ffmpeg manually and try again." >&2
    echo "If ffmpeg is already installed outside PATH, set TTS_FFMPEG_BIN to the directory containing ffmpeg." >&2
    return 1
}

setup_env() {
    if [ -f .env ]; then
        return 0
    fi

    echo
    echo "First setup"
    echo "1. Supertonic 3 CPU, lightweight, no voice cloning"
    echo "2. VoxCPM, heavier, supports voice cloning"
    printf "Select TTS engine [1-2]: "
    read -r engine_choice

    case "$engine_choice" in
        2) TTS_ENGINE_VALUE="voxcpm" ;;
        *) TTS_ENGINE_VALUE="supertonic3" ;;
    esac

    VOXCPM_DEVICE_VALUE="auto"
    VOXCPM_DTYPE_VALUE="auto"
    if [ "$TTS_ENGINE_VALUE" = "voxcpm" ]; then
        echo
        echo "1. Auto"
        if [ "$(uname -s)" = "Darwin" ]; then
            echo "2. CPU"
            echo "3. Apple Silicon MPS"
            printf "Select VoxCPM runtime [1-3]: "
            read -r runtime_choice
            case "$runtime_choice" in
                2)
                    VOXCPM_DEVICE_VALUE="cpu"
                    VOXCPM_DTYPE_VALUE="float32"
                    ;;
                3)
                    VOXCPM_DEVICE_VALUE="mps"
                    VOXCPM_DTYPE_VALUE="float32"
                    ;;
            esac
        else
            echo "2. CPU"
            echo "3. NVIDIA CUDA"
            printf "Select VoxCPM runtime [1-3]: "
            read -r runtime_choice
            case "$runtime_choice" in
                2)
                    VOXCPM_DEVICE_VALUE="cpu"
                    VOXCPM_DTYPE_VALUE="float32"
                    ;;
                3)
                    VOXCPM_DEVICE_VALUE="cuda"
                    VOXCPM_DTYPE_VALUE="float16"
                    ;;
            esac
        fi
    fi

    echo
    printf "Discord bot token: "
    read -r DISCORD_TOKEN_VALUE
    if [ -z "$DISCORD_TOKEN_VALUE" ]; then
        echo "DISCORD_TOKEN is required." >&2
        return 1
    fi

    cat > .env <<EOF
DISCORD_TOKEN=$DISCORD_TOKEN_VALUE
TTS_ENGINE=$TTS_ENGINE_VALUE
LOG_LEVEL=INFO
EOF

    if [ "$TTS_ENGINE_VALUE" = "voxcpm" ]; then
        {
            echo "VOXCPM_DEVICE=$VOXCPM_DEVICE_VALUE"
            echo "VOXCPM_DTYPE=$VOXCPM_DTYPE_VALUE"
        } >> .env
    fi
}

load_env() {
    if [ ! -f .env ]; then
        export TTS_ENGINE="${TTS_ENGINE:-supertonic3}"
        return 0
    fi

    set -a
    # shellcheck disable=SC1091
    . ./.env
    set +a
    export TTS_ENGINE="${TTS_ENGINE:-supertonic3}"
}

setup_uv() {
    if command_exists uv; then
        UV="$(command -v uv)"
        return 0
    fi

    setup_sudo
    case "$(uname -s)" in
        Darwin)
            if command_exists brew; then
                brew install uv && UV="$(command -v uv)" && return 0
            fi
            ;;
        Linux)
            if command_exists pacman; then
                run_privileged pacman -Sy --needed --noconfirm uv && UV="$(command -v uv)" && return 0
            fi
            if command_exists dnf; then
                run_privileged dnf install -y uv && UV="$(command -v uv)" && return 0
            fi
            if command_exists apk; then
                run_privileged apk add uv && UV="$(command -v uv)" && return 0
            fi
            ;;
    esac

    if command_exists curl; then
        echo "uv not found. Installing uv with the official installer..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
    elif command_exists wget; then
        echo "uv not found. Installing uv with the official installer..."
        wget -qO- https://astral.sh/uv/install.sh | sh
    else
        echo "uv not found and neither curl nor wget is available. Install uv manually and try again." >&2
        return 1
    fi

    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    if command_exists uv; then
        UV="$(command -v uv)"
        return 0
    fi

    echo "uv was installed, but the executable path was not found. Reopen this shell or add ~/.local/bin to PATH." >&2
    return 1
}

setup_uv_python() {
    setup_uv
    echo "Ensuring Python 3.11 is available via uv..."
    "$UV" python install 3.11
}

setup_venv() {
    if [ ! -x .venv/bin/python ]; then
        if [ -d .venv ]; then
            echo "Removing incomplete .venv..."
            rm -rf .venv
        fi
        echo
        echo "Creating .venv with uv..."
        "$UV" venv .venv --python 3.11
    fi

    if [ ! -x .venv/bin/python ]; then
        echo "Failed to create .venv correctly." >&2
        return 1
    fi

    echo "Installing dependencies with uv..."
    "$UV" pip install --python .venv/bin/python --upgrade pip

    engine_lower="$(printf '%s' "${TTS_ENGINE:-supertonic3}" | tr '[:upper:]' '[:lower:]')"
    if [ "$engine_lower" = "voxcpm" ]; then
        if use_cuda_torch; then
            "$UV" pip install --python .venv/bin/python torch torchaudio --index-url https://download.pytorch.org/whl/cu128
        else
            "$UV" pip install --python .venv/bin/python torch torchaudio
        fi
        "$UV" pip install --python .venv/bin/python -e ".[voxcpm]"
    else
        "$UV" pip install --python .venv/bin/python -e .
    fi
}

main() {
    setup_ffmpeg
    setup_env
    load_env
    setup_uv_python
    setup_venv

    echo
    echo "Starting Discord TTS bot with ${TTS_ENGINE} engine..."
    .venv/bin/python -c "from voxcpm_discord.app import main; main()"
}

main "$@"
