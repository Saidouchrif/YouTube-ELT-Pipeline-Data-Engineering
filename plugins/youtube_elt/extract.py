"""
YouTube Data Extraction Module.

This module handles the extraction of YouTube channel data using the YouTube Data API v3.
It includes functionality for retrieving video metadata, handling pagination,
managing API quotas, and implementing retry logic.
"""

import json
import time
import logging
import requests
import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from config.settings import config

# Configure logging
logging.basicConfig(level=getattr(logging, config.LOG_LEVEL))
logger = logging.getLogger(__name__)


class YouTubeAPIError(Exception):
    """Custom exception for YouTube API related errors."""
    pass


class QuotaExceededError(YouTubeAPIError):
    """Exception raised when API quota is exceeded."""
    pass


class YouTubeExtractor:
    """
    YouTube data extractor class.
    
    Handles extraction of video data from YouTube channels using the YouTube Data API v3.
    Includes quota management, pagination, and error handling.
    """
    
    def __init__(self, api_key: str = None, channel_handle: str = None):
        """
        Initialize the YouTube extractor.
        
        Args:
            api_key (str, optional): YouTube API key. Defaults to config value.
            channel_handle (str, optional): Channel handle. Defaults to config value.
        """
        self.api_key = api_key or config.YOUTUBE_API_KEY
        self.channel_handle = channel_handle or config.YOUTUBE_CHANNEL_HANDLE
        self.base_url = "https://www.googleapis.com/youtube/v3"
        self.quota_used = 0
        self.quota_limit = config.YOUTUBE_QUOTA_LIMIT
        
        if not self.api_key:
            raise YouTubeAPIError("YouTube API key is required")
        
        logger.info(f"Initialized YouTube extractor for channel: {self.channel_handle}")
    
    def _make_api_request(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make a request to the YouTube API with retry logic.
        
        Args:
            url (str): API endpoint URL
            params (Dict[str, Any]): Request parameters
            
        Returns:
            Dict[str, Any]: API response data
            
        Raises:
            YouTubeAPIError: If API request fails after retries
            QuotaExceededError: If API quota is exceeded
        """
        params['key'] = self.api_key
        
        for attempt in range(config.RETRY_ATTEMPTS):
            try:
                logger.debug(f"Making API request to {url}, attempt {attempt + 1}")
                response = requests.get(url, params=params, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check for API errors
                    if 'error' in data:
                        error_info = data['error']
                        if error_info.get('code') == 403 and 'quota' in error_info.get('message', '').lower():
                            raise QuotaExceededError(f"API quota exceeded: {error_info.get('message')}")
                        else:
                            raise YouTubeAPIError(f"API error: {error_info.get('message')}")
                    
                    # Update quota usage (approximate)
                    self.quota_used += self._estimate_quota_cost(url)
                    
                    logger.debug(f"API request successful, quota used: {self.quota_used}")
                    return data
                
                elif response.status_code == 403:
                    error_data = response.json()
                    if 'quota' in error_data.get('error', {}).get('message', '').lower():
                        raise QuotaExceededError("API quota exceeded")
                    else:
                        raise YouTubeAPIError(f"API access forbidden: {response.text}")
                
                elif response.status_code == 429:
                    # Rate limit exceeded, wait and retry
                    wait_time = config.RETRY_DELAY * (2 ** attempt)
                    logger.warning(f"Rate limit exceeded, waiting {wait_time} seconds")
                    time.sleep(wait_time)
                    continue
                
                else:
                    logger.warning(f"API request failed with status {response.status_code}: {response.text}")
                    if attempt == config.RETRY_ATTEMPTS - 1:
                        raise YouTubeAPIError(f"API request failed: {response.status_code} - {response.text}")
                    
                    time.sleep(config.RETRY_DELAY)
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request exception on attempt {attempt + 1}: {e}")
                if attempt == config.RETRY_ATTEMPTS - 1:
                    raise YouTubeAPIError(f"Request failed after {config.RETRY_ATTEMPTS} attempts: {e}")
                time.sleep(config.RETRY_DELAY)
        
        raise YouTubeAPIError("Max retry attempts exceeded")
    
    def _estimate_quota_cost(self, url: str) -> int:
        """
        Estimate the quota cost of an API request.
        
        Args:
            url (str): API endpoint URL
            
        Returns:
            int: Estimated quota cost
        """
        if 'channels' in url:
            return 1
        elif 'playlistItems' in url:
            return 1
        elif 'videos' in url:
            return 1
        else:
            return 1
    
    def get_channel_uploads_playlist_id(self) -> str:
        """
        Get the uploads playlist ID for the channel.
        
        Returns:
            str: Uploads playlist ID
            
        Raises:
            YouTubeAPIError: If channel not found or API error
        """
        url = f"{self.base_url}/channels"
        params = {
            'part': 'contentDetails',
            'forHandle': self.channel_handle
        }
        
        logger.info(f"Getting uploads playlist ID for channel: {self.channel_handle}")
        
        try:
            response_data = self._make_api_request(url, params)
            
            if not response_data.get('items'):
                raise YouTubeAPIError(f"Channel not found: {self.channel_handle}")
            
            uploads_playlist_id = response_data['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            logger.info(f"Found uploads playlist ID: {uploads_playlist_id}")
            
            return uploads_playlist_id
            
        except Exception as e:
            logger.error(f"Failed to get uploads playlist ID: {e}")
            raise
    
    def get_playlist_videos(self, playlist_id: str, max_results: int = None, 
                          page_token: str = None) -> Tuple[List[str], str]:
        """
        Get video IDs from a playlist with pagination support.
        
        Args:
            playlist_id (str): Playlist ID
            max_results (int, optional): Maximum results per page
            page_token (str, optional): Page token for pagination
            
        Returns:
            Tuple[List[str], str]: List of video IDs and next page token
        """
        url = f"{self.base_url}/playlistItems"
        params = {
            'part': 'contentDetails',
            'playlistId': playlist_id,
            'maxResults': max_results or config.YOUTUBE_MAX_RESULTS
        }
        
        if page_token:
            params['pageToken'] = page_token
        
        logger.debug(f"Getting videos from playlist: {playlist_id}")
        
        response_data = self._make_api_request(url, params)
        
        video_ids = [item['contentDetails']['videoId'] for item in response_data.get('items', [])]
        next_page_token = response_data.get('nextPageToken', '')
        
        logger.debug(f"Retrieved {len(video_ids)} video IDs")
        
        return video_ids, next_page_token
    
    def get_video_details(self, video_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Get detailed information for a list of video IDs.
        
        Args:
            video_ids (List[str]): List of video IDs
            
        Returns:
            List[Dict[str, Any]]: List of video details
        """
        if not video_ids:
            return []
        
        url = f"{self.base_url}/videos"
        video_ids_str = ",".join(video_ids)
        params = {
            'part': 'snippet,contentDetails,statistics',
            'id': video_ids_str
        }
        
        logger.debug(f"Getting details for {len(video_ids)} videos")
        
        response_data = self._make_api_request(url, params)
        
        videos = []
        for item in response_data.get('items', []):
            video = {
                'video_id': item['id'],
                'title': item['snippet']['title'],
                'description': item['snippet'].get('description', ''),
                'published_at': item['snippet']['publishedAt'],
                'duration': item['contentDetails']['duration'],
                'view_count': int(item['statistics'].get('viewCount', 0)),
                'like_count': int(item['statistics'].get('likeCount', 0)),
                'comment_count': int(item['statistics'].get('commentCount', 0)),
                'thumbnail_url': item['snippet']['thumbnails'].get('high', {}).get('url', ''),
                'channel_id': item['snippet']['channelId'],
                'channel_title': item['snippet']['channelTitle'],
                'tags': item['snippet'].get('tags', []),
                'category_id': item['snippet'].get('categoryId', ''),
                'default_language': item['snippet'].get('defaultLanguage', ''),
                'default_audio_language': item['snippet'].get('defaultAudioLanguage', '')
            }
            videos.append(video)
        
        logger.info(f"Retrieved details for {len(videos)} videos")
        
        return videos
    
    def extract_channel_videos(self, max_videos: int = None) -> Dict[str, Any]:
        """
        Extract all videos from the channel with pagination.
        
        Args:
            max_videos (int, optional): Maximum number of videos to extract
            
        Returns:
            Dict[str, Any]: Extracted channel data
        """
        logger.info(f"Starting extraction for channel: {self.channel_handle}")
        
        try:
            # Get uploads playlist ID
            uploads_playlist_id = self.get_channel_uploads_playlist_id()
            
            all_videos = []
            next_page_token = None
            videos_extracted = 0
            max_videos = max_videos or config.YOUTUBE_MAX_RESULTS
            
            while True:
                # Check quota before making request
                if self.quota_used >= self.quota_limit:
                    logger.warning(f"Approaching quota limit ({self.quota_used}/{self.quota_limit})")
                    break
                
                # Calculate remaining videos to fetch
                remaining_videos = max_videos - videos_extracted
                if remaining_videos <= 0:
                    break
                
                page_size = min(50, remaining_videos)  # YouTube API max is 50
                
                # Get video IDs from playlist
                video_ids, next_page_token = self.get_playlist_videos(
                    uploads_playlist_id, 
                    max_results=page_size,
                    page_token=next_page_token
                )
                
                if not video_ids:
                    break
                
                # Get video details in batches of 50 (API limit)
                batch_size = 50
                for i in range(0, len(video_ids), batch_size):
                    batch_ids = video_ids[i:i + batch_size]
                    video_details = self.get_video_details(batch_ids)
                    all_videos.extend(video_details)
                    videos_extracted += len(video_details)
                
                # Break if no more pages or reached max videos
                if not next_page_token or videos_extracted >= max_videos:
                    break
            
            # Prepare final data structure
            extraction_data = {
                'channel_handle': self.channel_handle,
                'extraction_date': datetime.datetime.utcnow().isoformat(),
                'total_videos': len(all_videos),
                'quota_used': self.quota_used,
                'videos': all_videos
            }
            
            logger.info(f"Extraction completed: {len(all_videos)} videos, quota used: {self.quota_used}")
            
            return extraction_data
            
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            raise
    
    def save_to_json(self, data: Dict[str, Any], output_path: str = None) -> str:
        """
        Save extracted data to JSON file with timestamp.
        
        Args:
            data (Dict[str, Any]): Data to save
            output_path (str, optional): Output directory path
            
        Returns:
            str: Path to saved file
        """
        if output_path is None:
            output_path = config.DATA_STAGING_PATH
        
        # Create output directory if it doesn't exist
        Path(output_path).mkdir(parents=True, exist_ok=True)
        
        # Generate timestamped filename
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"youtube_data_{self.channel_handle}_{timestamp}.json"
        file_path = Path(output_path) / filename
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Data saved to: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Failed to save data to {file_path}: {e}")
            raise


def extract_youtube_data(channel_handle: str = None, max_videos: int = None, 
                        output_path: str = None) -> str:
    """
    Main function to extract YouTube data and save to JSON.
    
    Args:
        channel_handle (str, optional): YouTube channel handle
        max_videos (int, optional): Maximum number of videos to extract
        output_path (str, optional): Output directory path
        
    Returns:
        str: Path to saved JSON file
    """
    extractor = YouTubeExtractor(channel_handle=channel_handle)
    data = extractor.extract_channel_videos(max_videos=max_videos)
    file_path = extractor.save_to_json(data, output_path=output_path)
    
    return file_path


if __name__ == "__main__":
    # Example usage
    try:
        file_path = extract_youtube_data(max_videos=10)
        print(f"Data extracted and saved to: {file_path}")
    except Exception as e:
        print(f"Extraction failed: {e}")
