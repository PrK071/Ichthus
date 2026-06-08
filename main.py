import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
VENV_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"


def _running_inside_project_venv() -> bool:
    try:
        return Path(sys.executable).resolve() == VENV_PYTHON.resolve()
    except OSError:
        return False


def _relaunch_with_project_venv() -> bool:
    if _running_inside_project_venv() or not VENV_PYTHON.exists():
        return False

    subprocess.Popen(
        [str(VENV_PYTHON), str(Path(__file__).resolve())],
        cwd=str(ROOT),
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return True


def main():
    if _relaunch_with_project_venv():
        return

    from gui import MusicRecognizerApp

    app = MusicRecognizerApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()
