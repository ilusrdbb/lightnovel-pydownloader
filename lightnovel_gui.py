import sys


def _get_text(key: str, default: str) -> str:
    try:
        from src.services.text_catalog import get_text_catalog
    except Exception:
        return default
    try:
        return get_text_catalog().get_text(key, default=default)
    except Exception:
        return default


def main() -> int:
    try:
        from ui.main import main as gui_main
    except ModuleNotFoundError as exc:
        if exc.name and exc.name.startswith("PySide6"):
            print(
                _get_text(
                    "dialog.dependency_missing_pyside6",
                    "未安装 PySide6。\n请先在终端执行：pip install -r requirements-gui.txt",
                )
            )
            return 1
        if exc.name and exc.name.startswith("ruamel"):
            print(
                _get_text(
                    "dialog.dependency_missing_ruamel",
                    "未安装 ruamel.yaml。\n请先在终端执行：pip install -r requirements-gui.txt",
                )
            )
            return 1
        raise

    return gui_main()


if __name__ == "__main__":
    sys.exit(main())
