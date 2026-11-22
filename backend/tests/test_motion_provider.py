from pathlib import Path
from urllib.parse import urlparse

def test_motion_output_host_allowlist():
    assert urlparse("https://abc.replicate.delivery/video.mp4").hostname.endswith(".replicate.delivery")
    assert urlparse("https://replicate.delivery/video.mp4").hostname == "replicate.delivery"
    assert not (urlparse("https://example.com/video.mp4").hostname.endswith(".replicate.delivery"))
