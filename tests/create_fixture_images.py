

"""Generate deterministic placeholder images for MoodCut tests."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parents[1]
IMAGE_DIR = PROJECT_ROOT / "tests" / "fixtures" / "images"

IMAGE_SIZE = (640, 640)


def create_placeholder(filename, label, background_color):
    """Create a labeled placeholder PNG image."""

    IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    image = Image.new(
        "RGB",
        IMAGE_SIZE,
        color=background_color,
    )

    draw = ImageDraw.Draw(image)

    font = ImageFont.load_default(size=120)

    draw.text(
        (IMAGE_SIZE[0] // 2, IMAGE_SIZE[1] // 2),
        label,
        fill="white",
        font=font,
        anchor="mm",
    )

    output_path = IMAGE_DIR / filename

    image.save(output_path, format="PNG")

    print(f"Created: {output_path}")


def main():
    create_placeholder(
        filename="dev_a.png",
        label="A",
        background_color=(70, 120, 185),
    )

    create_placeholder(
        filename="dev_b.png",
        label="B",
        background_color=(190, 95, 115),
    )


if __name__ == "__main__":
    main()
