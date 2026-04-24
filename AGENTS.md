# AGENTS

## Environment

1. 이 저장소는 Windows 기준으로 `.venv`를 사용한다.
2. `.venv`가 없으면 `start.bat`이 자동으로 생성하고 의존성을 설치한다.
3. Python 명령은 가능하면 `.venv\Scripts\python.exe ...` 형태로 실행한다.
4. 현재 기본 작업 환경은 Linux가 아니라 Windows다.

## Project Notes

1. 기본 런타임은 Python 3.11이다.
2. Discord 봇 토큰은 `DISCORD_TOKEN` 환경 변수로 주입한다.
3. VoxCPM 기본 모델은 `openbmb/VoxCPM2`다.
4. 음성 재생을 위해 시스템 `ffmpeg`가 필요하다.
5. `triton`처럼 Linux 전용 wheel에 의존하는 패키지는 Windows에서 바로 추가/설치되지 않을 수 있다.

## Implementation Constraints

1. 프로젝트가 직접 생성/관리하는 모델 관련 파일(예: override 설정, 부가 산출물)은 로컬 `data/` 아래에 저장한다.
2. Hugging Face 모델 원본 다운로드/캐시는 프로젝트 로컬이 아니라 Hugging Face 내부 공통 캐시를 사용한다.
3. 사용자의 음성 설정, 캐시, 생성 음성, 음성 샘플은 로컬 `data-user/` 아래에 저장한다.
4. 전체 테스트 스위트는 기본적으로 돌리지 않는다.
5. 빠른 검증이 필요하면 문법 검사 수준의 가벼운 확인만 수행한다.
