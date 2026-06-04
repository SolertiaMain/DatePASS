from pathlib import Path


def test_required_assets_exist():
    root = Path(__file__).parents[1]
    for name in ["icon.png", "icon@2x.png", "logo.png", "logo@2x.png"]:
        assert (root / "app" / "assets" / name).exists()
