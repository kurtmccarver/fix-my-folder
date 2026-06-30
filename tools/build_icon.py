from pathlib import Path

from PIL import Image


def main() -> None:
    source = Path("assets/logo.png")
    icon = Path("assets/logo.ico")
    if not source.exists():
        raise SystemExit("assets/logo.png not found")

    image = Image.open(source).convert("RGBA")
    image.save(
        icon,
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(f"Built {icon}")


if __name__ == "__main__":
    main()
