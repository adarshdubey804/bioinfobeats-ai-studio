from app.api.routes.media import _matches_signature


def test_accepts_supported_image_signatures():
    assert _matches_signature(b"\\xff\\xd8\\xffpayload", "image", "image/jpeg")
    assert _matches_signature(b"\\x89PNG\\r\\n\\x1a\\npayload", "image", "image/png")
    assert _matches_signature(b"RIFFxxxxWEBPpayload", "image", "image/webp")


def test_rejects_mime_spoofed_uploads():
    assert not _matches_signature(b"not really a png", "image", "image/png")
    assert not _matches_signature(b"\\xff\\xd8\\xffpayload", "video", "video/mp4")


def test_accepts_audio_and_video_signatures():
    assert _matches_signature(b"RIFFxxxxWAVEpayload", "audio", "audio/wav")
    assert _matches_signature(b"OggSpayload", "audio", "audio/ogg")
    assert _matches_signature(b"ID3payload", "audio", "audio/mpeg")
    assert _matches_signature(b"\\x00\\x00\\x00\\x18ftypisom", "video", "video/mp4")
    assert _matches_signature(b"\\x1a\\x45\\xdf\\xa3payload", "video", "video/webm")
