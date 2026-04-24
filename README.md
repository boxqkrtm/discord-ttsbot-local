# VoxCPM Discord Bot

Windows 11에서 VoxCPM2로 디스코드 음성 TTS를 실행하는 봇입니다.

## 빠른시작

1. `start.bat` 파일을 더블 클릭합니다.
2. 필요한 경우 `start.bat`이 `uv`, Python 3.11, `ffmpeg`, `.venv`를 자동으로 설치/준비합니다.
3. 화면 안내대로 CPU/CUDA를 선택하고 디스코드 봇 토큰을 입력합니다.

## 권장 환경

- Windows 11
- `winget` 사용 가능 환경
- CUDA 가속 지원 기기: GTX 1060 6GB 이상, RTX 3060~3090, RTX 4060~4090, RTX 5060~5090
- RTX 50 시리즈는 최신 NVIDIA 드라이버 권장
- 디스코드 봇 토큰

## 실행

```bat
start.bat
```

처음 실행하면 `start.bat`이 아래 작업을 자동으로 처리합니다.

- `ffmpeg` 확인, 없으면 `winget install -e --id Gyan.FFmpeg`로 설치
- `uv` 확인, 없으면 `winget install -e --id Astral-sh.uv`로 설치
- `uv`로 Python 3.11 준비
- `.env`가 없으면 CPU/CUDA 선택
- 디스코드 봇 토큰 입력 후 `.env` 생성
- `uv`로 `.venv` 생성 및 필요한 패키지 설치
- 봇 실행

## 사용법

1. 디스코드에서 봇을 서버에 초대합니다.
- https://discord.com/developers/applications 에서 생성
2. `start.bat`을 실행합니다.
3. 처음 실행 시 안내에 따라 CPU/CUDA를 선택합니다 (CUDA 무조건 추천)
4. 봇 토큰을 입력합니다.
- 봇 토큰 받는법) 위의 봇 페이지에서 봇선택=>봇=>토큰
4. 디스코드 음성 채널에 들어갑니다.
5. `/들어와` 명령으로 봇을 음성 채널에 입장시킵니다.
6. 같은 텍스트 채널에 문장을 입력하면 봇이 음성으로 읽습니다.

## 명령어

- `/들어와`: 현재 음성 채널에 봇 입장
- `/나가`: 봇 퇴장
- `/생성`: 텍스트를 wav 파일로 생성
- `/설정`: 음성 스타일 또는 클로닝 음성 설정
- `/멈춰`: 현재 재생 중지 및 대기열 삭제

## 폴더

- `data/`: 프로젝트가 생성한 모델 override 등 보조 파일
- `data-user/`: 사용자 설정, 생성 음성, 음성 샘플

참고:
- Hugging Face 모델 원본 다운로드/캐시는 프로젝트 폴더가 아니라 Hugging Face 공통 캐시를 사용합니다.

## 문제해결
- `.env` 파일 삭제 시 처음 안내를 다시 볼 수 있습니다.
- `start.bat`은 `uv`, Python 3.11, `ffmpeg`를 자동 설치하려고 시도합니다.
- 자동 설치가 실패하면 `winget`이 정상 동작하는지 확인한 뒤 다시 실행해 보세요.
- `winget` 설치 직후 경로 반영이 늦으면 `start.bat`을 한 번 더 실행해 보세요.
- 디스코드 채팅을 바로 봇이 받으려면, 디스코드 봇 권한에 Presence Intent가 필요합니다.
