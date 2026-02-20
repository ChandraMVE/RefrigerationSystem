from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / "src"))

from refrigeration.app import SimulationApp


if __name__ == "__main__":
    if "--demo" in sys.argv:
        SimulationApp().demo()
    else:
        try:
            from refrigeration.gui import run_gui
        except ModuleNotFoundError as exc:
            if exc.name == "PyQt6":
                print("PyQt6 is required for GUI mode. Install it with: pip install PyQt6")
                raise SystemExit(1)
            raise

        raise SystemExit(run_gui())
