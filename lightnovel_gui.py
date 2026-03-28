import sys


def main() -> int:
    try:
        from ui.main import main as gui_main
    except ModuleNotFoundError as exc:
        if exc.name and exc.name.startswith("PySide6"):
            print("未安装 PySide6，请先执行: pip install -r requirements-gui.txt")
            return 1
        if exc.name and exc.name.startswith("ruamel"):
            print("未安装 ruamel.yaml，请先执行: pip install -r requirements-gui.txt")
            return 1
        raise

    return gui_main()


if __name__ == "__main__":
    sys.exit(main())
