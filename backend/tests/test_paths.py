from pathlib import Path

from app.core.errors import InvalidInputError
from app.core.paths import IMAGE_EXTENSIONS, safe_join, validate_relative_path


def _rejects(value, exts=None):
    try:
        validate_relative_path(value, exts)
    except InvalidInputError:
        return True
    return False


def test_rejects_unsafe_paths():
    for bad in ("../x.png", "a/../../x.png", "/etc/passwd", "C:\\Windows\\x.png", "\\\\server\\share\\x.png",
                "", "   ", "a\x00b.png", ".."):
        assert _rejects(bad), bad


def test_accepts_and_normalises():
    assert validate_relative_path("fox\\ref.PNG", IMAGE_EXTENSIONS) == "fox/ref.PNG"
    assert validate_relative_path("./a/b.jpg", IMAGE_EXTENSIONS) == "a/b.jpg"


def test_extension_filter():
    assert _rejects("script.py", IMAGE_EXTENSIONS)


def test_safe_join_stays_inside(tmp_path=None):
    import tempfile
    base = Path(tempfile.mkdtemp())
    assert str(safe_join(base, "a/b.png")).startswith(str(base.resolve()))
    try:
        safe_join(base, "../outside.png")
    except InvalidInputError:
        return
    raise AssertionError("escaped base")
