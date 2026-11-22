from pathlib import Path
from types import SimpleNamespace

from app.api.routes.media import _item
from app.core.config import settings
from app.main import app


def test_library_asset_urls_require_authenticated_api_route():
    asset = SimpleNamespace(
        id="asset-123",
        user_id="owner-123",
        filename="private-reference.png",
        media_type="image",
        content_type="image/png",
        size_bytes=128,
        created_at=__import__("datetime").datetime(2026, 1, 1),
    )
    assert _item(asset)["url"] == "/api/v1/media/library/asset-123/file"


def test_static_media_mount_exposes_only_public_directory():
    media_mount = next(route for route in app.routes if getattr(route, "name", None) == "media")
    assert Path(media_mount.directory).resolve() == (Path(settings.media_storage_dir).resolve() / "public").resolve()
    assert Path(media_mount.directory).name == "public"


def test_private_media_storage_is_separate_from_public_media():
    public_root = (Path(settings.media_storage_dir).resolve() / "public").resolve()
    private_root = Path(settings.private_media_storage_dir).resolve()
    assert public_root != private_root
    assert public_root not in private_root.parents
