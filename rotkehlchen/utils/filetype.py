from pathlib import Path


def guess_icon_extension(filepath: Path) -> str | None:
    """Detect the image type from a file's magic bytes / header.

    Vendored replacement for the ``filetype`` library, covering only the
    icon formats supported by rotki (PNG, JPEG, WebP, SVG).

    Returns the canonical extension (with leading dot) for supported types,
    or None if the file type cannot be determined.
    """
    try:
        with open(filepath, 'rb') as f:
            header = f.read(12)
    except OSError:
        return None

    if len(header) < 4:
        return None

    # PNG: \x89PNG\r\n\x1a\n
    if header[:8] == b'\x89PNG\r\n\x1a\n':
        return '.png'

    # JPEG: \xff\xd8\xff
    if header[:3] == b'\xff\xd8\xff':
        return '.jpg'

    # WebP: RIFF .... WEBP
    if header[:4] == b'RIFF' and len(header) >= 12 and header[8:12] == b'WEBP':
        return '.webp'

    # SVG: text-based (try decoding the header as utf-8)
    try:
        text_header = header.decode('utf-8').lstrip()
    except UnicodeDecodeError:
        return None

    if text_header.startswith(('<?xml', '<svg')):
        return '.svg'

    return None
