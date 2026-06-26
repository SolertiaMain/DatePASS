from app.photos import PHOTO_MAX_BYTES, sanitize_filename, validate_photo


def test_photo_file_required():
    try:
        validate_photo(b"", "empty.jpg")
    except ValueError as exc:
        assert str(exc) == "Photo file is required"
    else:
        raise AssertionError("Expected validation error")


def test_photo_format_invalid():
    try:
        validate_photo(b"not-an-image", "note.txt")
    except ValueError as exc:
        assert str(exc) == "Unsupported image format"
    else:
        raise AssertionError("Expected validation error")


def test_photo_too_large():
    try:
        validate_photo(b"\xff\xd8\xff" + (b"x" * PHOTO_MAX_BYTES), "huge.jpg")
    except ValueError as exc:
        assert str(exc) == "Photo exceeds the 10 MB limit"
    else:
        raise AssertionError("Expected validation error")


def test_jpeg_photo_validates_and_sanitizes_name():
    photo = validate_photo(b"\xff\xd8\xffphoto", "../first date!!.jpg")
    assert photo.content_type == "image/jpeg"
    assert photo.extension == "jpg"
    assert photo.filename == "first-date-.jpg"


def test_png_photo_validates():
    photo = validate_photo(b"\x89PNG\r\n\x1a\nxxxxIHDRphoto", "memory.png")
    assert photo.content_type == "image/png"
    assert photo.extension == "png"


def test_sanitize_filename_has_fallback():
    assert sanitize_filename("///") == "memory-photo"
