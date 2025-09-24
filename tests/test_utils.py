from plugins.youtube_elt.db import utcnow_iso
from plugins.youtube_elt.extract import YouTubeExtractor
import pytest
from unittest.mock import patch
import json
from pathlib import Path


def test_utcnow_iso_format():
    ts = utcnow_iso()
    assert ts.endswith("Z") and "T" in ts


def test_load_staging_file_not_found(tmp_path):
    from plugins.youtube_elt.load import load_staging_from_file
    with pytest.raises(FileNotFoundError):
        load_staging_from_file(str(tmp_path / "does_not_exist.json"))


@patch("requests.get")
def test_save_to_json_writes_file(mget, tmp_path, monkeypatch):
    # Mock channel and playlist + videos flow minimally
    monkeypatch.setenv("YOUTUBE_API_KEY", "key")

    # 1st call (channels)
    resp_channels = {"items": [{"contentDetails": {"relatedPlaylists": {"uploads": "UU_123"}}}]}
    # 2nd call (playlistItems)
    resp_playlist = {"items": [{"contentDetails": {"videoId": "vid1"}}]}
    # 3rd call (videos)
    resp_videos = {
        "items": [{
            "id": "vid1",
            "snippet": {
                "title": "T",
                "publishedAt": "2024-01-01T00:00:00Z",
                "thumbnails": {"high": {"url": "u"}},
                "channelId": "c",
                "channelTitle": "ct"
            },
            "contentDetails": {"duration": "PT1M"},
            "statistics": {"viewCount": "10", "likeCount": "1", "commentCount": "0"}
        }]
    }

    def side_effect(url, params=None, timeout=30):
        if "channels" in url:
            return _mock(200, resp_channels)
        if "playlistItems" in url:
            return _mock(200, resp_playlist)
        if "videos" in url:
            return _mock(200, resp_videos)
        return _mock(404, {})

    def _mock(code, js):
        class R:
            status_code = code
            def __init__(self, j):
                self._j = j
                self.text = json.dumps(j)
            def json(self):
                return self._j
        return R(js)

    mget.side_effect = side_effect

    ext = YouTubeExtractor(channel_handle="MrBeast")
    data = ext.extract_channel_videos(max_videos=1)
    out = ext.save_to_json(data, output_path=str(tmp_path))
    p = Path(out)
    assert p.exists() and p.suffix == ".json"
