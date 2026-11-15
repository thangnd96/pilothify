"""Images, audio and video in an app's asset folders stay out of the semantic pass.

Each image is one LLM vision call and each audio/video file a transcription. A
game corpus held 2,702 sprites under `assets-src/` and a dozen sound effects:
thousands of calls that describe artwork and sounds no code question needs.
Asset media are now reported instead of extracted; files in docs-like folders
are kept, and PILOTHIFY_ASSET_MEDIA=1 keeps everything.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from pilothify.detect import detect

_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
_MP3 = b"ID3\x03\x00\x00\x00" + b"\x00" * 32


def _touch(root: Path, rel: str, data: bytes = _PNG) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)


def _names(paths: list[str]) -> list[str]:
    return sorted(Path(p).name for p in paths)


@pytest.fixture(autouse=True)
def _default_env(monkeypatch):
    monkeypatch.delenv("PILOTHIFY_ASSET_MEDIA", raising=False)


def test_app_asset_images_stay_out_of_the_semantic_pass(tmp_path):
    _touch(tmp_path, "apps/game/assets-src/hero.png")
    _touch(tmp_path, "domains/social/src/assets/avatars/a.webp")
    _touch(tmp_path, "apps/admin/public/logo.svg", b"<svg xmlns='http://www.w3.org/2000/svg'/>")
    (tmp_path / "app.ts").write_text("export const a = 1;\n", encoding="utf-8")
    result = detect(tmp_path)
    assert result["files"]["image"] == []
    assert _names(result["skipped_asset_media"]) == ["a.webp", "hero.png", "logo.svg"]


def test_app_asset_audio_and_video_stay_out_of_the_semantic_pass(tmp_path):
    _touch(tmp_path, "apps/game/public/sfx/coin.mp3", _MP3)
    _touch(tmp_path, "apps/game/assets/intro.mp4", b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 16)
    result = detect(tmp_path)
    assert result["files"]["video"] == []
    assert _names(result["skipped_asset_media"]) == ["coin.mp3", "intro.mp4"]


def test_media_in_docs_folders_are_kept_even_inside_an_asset_tree(tmp_path):
    _touch(tmp_path, "docs/architecture.png")
    _touch(tmp_path, "assets/docs/flow.png")
    _touch(tmp_path, "screenshots/home.png")
    _touch(tmp_path, "whiteboard.jpg")
    _touch(tmp_path, "docs/demo-walkthrough.mp3", _MP3)
    result = detect(tmp_path)
    assert _names(result["files"]["image"]) == ["architecture.png", "flow.png", "home.png", "whiteboard.jpg"]
    assert _names(result["files"]["video"]) == ["demo-walkthrough.mp3"]
    assert result["skipped_asset_media"] == []


def test_the_env_switch_keeps_asset_media(tmp_path, monkeypatch):
    monkeypatch.setenv("PILOTHIFY_ASSET_MEDIA", "1")
    _touch(tmp_path, "assets/hero.png")
    _touch(tmp_path, "assets/theme.ogg", b"OggS" + b"\x00" * 32)
    result = detect(tmp_path)
    assert _names(result["files"]["image"]) == ["hero.png"]
    assert _names(result["files"]["video"]) == ["theme.ogg"]
    assert result["skipped_asset_media"] == []
