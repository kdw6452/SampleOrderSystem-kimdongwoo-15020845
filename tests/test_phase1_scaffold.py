import subprocess
import sys
from unittest.mock import patch, MagicMock


def test_packages_importable() -> None:
    import models
    import views
    import controllers
    import data


def test_main_runs_main_controller(capsys: object) -> None:
    """Phase 4: main()은 MainController.run()을 호출한다."""
    from main import main
    mock_ctrl = MagicMock()
    mock_ctrl.run.side_effect = SystemExit(0)
    with patch("controllers.main_controller.MainController", return_value=mock_ctrl):
        try:
            main()
        except SystemExit:
            pass
    mock_ctrl.run.assert_called_once()


def test_main_exits_zero() -> None:
    """Phase 4: MainController를 Mock으로 교체하면 returncode 0으로 종료."""
    script = (
        "from unittest.mock import patch, MagicMock\n"
        "from main import main\n"
        "mock_ctrl = MagicMock()\n"
        "mock_ctrl.run.return_value = None\n"
        "with patch('controllers.main_controller.MainController', return_value=mock_ctrl):\n"
        "    main()\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 0
