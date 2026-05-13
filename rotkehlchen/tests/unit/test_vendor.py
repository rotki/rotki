from pathlib import Path

from rotkehlchen.utils.filetype import guess_icon_extension

IMAGES_DIR = Path(__file__).resolve().parent.parent / 'data' / 'images'


def _write_temp_file(dirpath: Path, name: str, content: bytes) -> Path:
    filepath = dirpath / name
    filepath.write_bytes(content)
    return filepath


def test_guess_png() -> None:
    """PNG files are detected by their magic bytes."""
    png_path = IMAGES_DIR / 'MON_small.png'
    assert guess_icon_extension(png_path) == '.png'


def test_guess_svg() -> None:
    """SVG files are detected by their header text."""
    svg_path = (
        IMAGES_DIR
        / 'eip155%3A57073%2Ferc20%3A0x0200C29006150606B650577BBE7B6248F58470c1_small.svg'
    )
    assert guess_icon_extension(svg_path) == '.svg'


def test_guess_jpeg(tmp_path: Path) -> None:
    """JPEG files are detected by their magic bytes."""
    jpg_path = _write_temp_file(tmp_path, 'test.jpg', b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01')
    assert guess_icon_extension(jpg_path) == '.jpg'


def test_guess_webp(tmp_path: Path) -> None:
    """WebP files are detected by their RIFF container header."""
    webp_path = _write_temp_file(tmp_path, 'test.webp', b'RIFF\x14\x00\x00\x00WEBPVP8')
    assert guess_icon_extension(webp_path) == '.webp'


def test_guess_svg_xml_declaration(tmp_path: Path) -> None:
    """SVG files starting with an XML declaration are detected."""
    svg_path = _write_temp_file(tmp_path, 'test.svg', b'<?xml version="1.0"?><svg></svg>')
    assert guess_icon_extension(svg_path) == '.svg'


def test_guess_invalid_file(tmp_path: Path) -> None:
    """Files that don't match any known format return None."""
    invalid_path = _write_temp_file(tmp_path, 'test.bin', b'abcd')
    assert guess_icon_extension(invalid_path) is None


def test_guess_empty_file(tmp_path: Path) -> None:
    """Empty files return None."""
    empty_path = _write_temp_file(tmp_path, 'empty.bin', b'')
    assert guess_icon_extension(empty_path) is None


def test_guess_nonexistent_file(tmp_path: Path) -> None:
    """Non-existent files return None (OSError caught)."""
    assert guess_icon_extension(tmp_path / 'does_not_exist.png') is None
