"""ai_router: 로컬 LLM 라우팅 실험 패키지."""


def main() -> None:
    # pyproject.toml 의 [project.scripts] 에서 `ai-router` 명령이 이 함수를 호출합니다.
    import sys

    from ai_router.cli import main as cli_main

    sys.exit(cli_main())
