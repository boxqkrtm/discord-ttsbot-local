# discord-ttsbot-local

Windows, macOS, Linux에서 로컬 TTS로 디스코드 음성 읽기를 실행하는 봇입니다. 최초 실행 시 `supertonic3` 또는 `voxcpm` 엔진을 선택할 수 있습니다.

## 엔진

- `supertonic3`: 기본 추천. CPU/ONNX 기반이라 설치와 배포가 가볍습니다. 보이스 클로닝은 지원하지 않고, 내장 음성 스타일(`M1`-`M5`, `F1`-`F5`) 또는 Supertonic 스타일 JSON을 사용합니다.
- `voxcpm`: 무겁지만 기존 wav/mp3/ogg 기반 보이스 클로닝 설정을 지원합니다. CPU 또는 CUDA를 선택할 수 있습니다.

## 빠른시작

1. Windows는 `start.bat` 파일을 더블 클릭합니다.
2. macOS/Linux는 터미널에서 `./start.sh`를 실행합니다.
3. 필요한 경우 실행 스크립트가 `uv`, Python 3.11, `ffmpeg`, `.venv`를 자동으로 설치/준비합니다.
4. 화면 안내대로 TTS 엔진을 선택하고 디스코드 봇 토큰을 입력합니다.

## 권장 환경

- Windows 11, macOS, 또는 Linux
- Windows: `winget` 사용 가능 환경
- macOS: Homebrew 권장
- Linux: 배포판 패키지 매니저 또는 `sudo` 사용 가능 환경 권장
- 디스코드 봇 토큰
- Supertonic 3 사용 시 일반 CPU 환경
- VoxCPM CUDA 사용 시 NVIDIA GPU와 최신 드라이버

## 실행

Windows:

```bat
start.bat
```

macOS/Linux:

```sh
./start.sh
```

처음 실행하면 스크립트가 아래 작업을 자동으로 처리합니다.

- `ffmpeg` 확인 및 자동 설치 시도
  - Windows: `winget`
  - macOS: `brew`, `port`
  - Linux: `apt-get`, `dnf`, `yum`, `pacman`, `zypper`, `apk`, `xbps-install`, `emerge`, `nix-env`, `snap`
- `uv` 확인 및 자동 설치 시도
  - Windows: `winget`
  - macOS/Linux: `brew`, 일부 배포판 패키지 매니저, 또는 Astral 공식 설치 스크립트
- `uv`로 Python 3.11 준비
- `.env`가 없으면 `supertonic3`/`voxcpm` 엔진 선택
- VoxCPM 선택 시 Auto/CPU/CUDA 선택
  - Auto는 `nvidia-smi` 또는 `nvcc`가 있으면 CUDA용 PyTorch wheel을 설치합니다.
  - CUDA를 직접 선택하면 CUDA용 PyTorch wheel을 설치하고, 런타임에서 CUDA 사용 가능 여부를 확인합니다.
- 디스코드 봇 토큰 입력 후 `.env` 생성
- 선택한 엔진에 필요한 패키지 설치
- 봇 실행

## 설정 예시

일반 사용자는 `.env`를 직접 만질 필요가 거의 없습니다. `start.bat` 또는 `start.sh`가 필요한 최소값만 생성합니다.

Supertonic 3 기본:

```env
TTS_ENGINE=supertonic3
```

VoxCPM:

```env
TTS_ENGINE=voxcpm
```

공통으로 필요한 값은 봇 토큰뿐입니다. 엔진별 세부값은 코드 기본값으로 동작합니다.

```env
DISCORD_TOKEN=your-token-here
LOG_LEVEL=INFO
```

## 사용법

1. 디스코드에서 봇을 서버에 초대합니다.
- https://discord.com/developers/applications 에서 생성
2. Windows는 `start.bat`, macOS/Linux는 `./start.sh`를 실행합니다.
3. 봇 토큰을 입력합니다.
- 봇 토큰 받는법) 위의 봇 페이지에서 봇선택=>봇=>토큰
4. 디스코드 음성 채널에 들어갑니다.
5. `/들어와` 명령으로 봇을 음성 채널에 입장시킵니다.
6. 같은 텍스트 채널에 문장을 입력하면 봇이 음성으로 읽습니다.

## 명령어

- `/들어와`: 현재 음성 채널에 봇 입장
- `/나가`: 봇 퇴장
- `/생성`: 텍스트를 wav 음성 파일로 생성
- `/설정`: 현재 엔진의 음성 설정 저장
  - Supertonic 3: `M1`-`M5`, `F1`-`F5` 스타일 또는 JSON 스타일 파일
  - VoxCPM: 스타일 프롬프트 또는 wav/mp3/ogg 보이스 클로닝 파일
- `/멈춰`: 현재 재생 중지 및 대기열 삭제

## 폴더

- `data/`: 프로젝트가 생성한 모델 관련 보조 파일
- `data-user/`: 사용자 설정, 생성 음성, 음성 샘플

참고:
- Hugging Face 모델 원본 다운로드/캐시는 프로젝트 폴더가 아니라 Hugging Face 공통 캐시를 사용할 수 있습니다.
- `.env` 파일 삭제 시 처음 안내를 다시 볼 수 있습니다.
