import subprocess
import sys


def test_packages_importable() -> None:
    import models
    import views
    import controllers
    import data


def test_main_prints_system_start(capsys: object) -> None:
    from main import main
    main()
    captured = getattr(capsys, "readouterr")()
    assert "시스템 시작" in captured.out


def test_main_exits_zero() -> None:
    result = subprocess.run(
        [sys.executable, "main.py"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0
    assert "시스템 시작" in result.stdout
