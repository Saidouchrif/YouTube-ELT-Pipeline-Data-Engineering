import json
from unittest.mock import patch

import pytest

from plugins.youtube_elt.extract import YouTubeExtractor, YouTubeAPIError, QuotaExceededError


def mock_response(status=200, json_data=None):
    class R:
        def __init__(self):
            self.status_code = status
            self._json = json_data or {}
            self.text = json.dumps(self._json)

        def json(self):
            return self._json

    return R()


@patch("requests.get")
@pytest.mark.parametrize("handle", ["MrBeast"])
def test_get_channel_uploads_playlist_id_success(mget, handle, monkeypatch):
    # channels endpoint
    mget.return_value = mock_response(200, {
        "items": [{"contentDetails": {"relatedPlaylists": {"uploads": "UU_123"}}}]
    })
    monkeypatch.setenv("YOUTUBE_API_KEY", "key")
    ext = YouTubeExtractor(channel_handle=handle)
    pid = ext.get_channel_uploads_playlist_id()
    assert pid == "UU_123"


@patch("requests.get")
def test_get_channel_uploads_playlist_id_not_found(mget, monkeypatch):
    mget.return_value = mock_response(200, {"items": []})
    monkeypatch.setenv("YOUTUBE_API_KEY", "key")
    ext = YouTubeExtractor(channel_handle="unknown")
    with pytest.raises(YouTubeAPIError):
        ext.get_channel_uploads_playlist_id()


@patch("requests.get")
def test_quota_exceeded_raises(mget, monkeypatch):
    mget.return_value = mock_response(403, {"error": {"code": 403, "message": "quota exceeded"}})
    monkeypatch.setenv("YOUTUBE_API_KEY", "key")
    ext = YouTubeExtractor(channel_handle="MrBeast")
    with pytest.raises(QuotaExceededError):
        ext.get_channel_uploads_playlist_id()


@patch("requests.get")
def test_get_video_details_success(mget, monkeypatch):
    # videos endpoint
    mget.return_value = mock_response(200, {
        "items": [{
            "id": "abc",
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
    })
    monkeypatch.setenv("YOUTUBE_API_KEY", "key")
    ext = YouTubeExtractor(channel_handle="MrBeast")
    out = ext.get_video_details(["abc"]) 
    assert out and out[0]["video_id"] == "abc"
