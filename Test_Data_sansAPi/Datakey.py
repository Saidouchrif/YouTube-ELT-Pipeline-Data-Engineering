import requests
import datetime
import json

# ======================
# 1. Informations de base
# ======================
API_KEY = "AIzaSyAr6B9F18e9vrR5_5sp4dDIVulnup3cqXc"  # Remplacez par votre clé API
CHANNEL_HANDLE = "MrBeast"  # Identifiant ou pseudo de la chaîne
MAX_RESULTS = 5  # Nombre de vidéos à récupérer

# ======================
# 2. Récupérer le playlistId des vidéos uploadées
# ======================
url_channel = f"https://www.googleapis.com/youtube/v3/channels?part=contentDetails&forHandle={CHANNEL_HANDLE}&key={API_KEY}"
response_channel = requests.get(url_channel).json()

uploads_playlist_id = response_channel["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

# ======================
# 3. Récupérer les dernières vidéos de la playlist
# ======================
url_playlist = f"https://www.googleapis.com/youtube/v3/playlistItems?part=contentDetails&playlistId={uploads_playlist_id}&maxResults={MAX_RESULTS}&key={API_KEY}"
response_playlist = requests.get(url_playlist).json()

video_ids = [item["contentDetails"]["videoId"] for item in response_playlist["items"]]

# ======================
# 4. Récupérer les détails et statistiques des vidéos
# ======================
video_ids_str = ",".join(video_ids)
url_videos = f"https://www.googleapis.com/youtube/v3/videos?part=snippet,contentDetails,statistics&id={video_ids_str}&key={API_KEY}"
response_videos = requests.get(url_videos).json()

# ======================
# 5. Construire le JSON final
# ======================
data = {
    "channel_handle": CHANNEL_HANDLE,
    "extraction_date": datetime.datetime.utcnow().isoformat(),
    "total_videos": len(response_videos["items"]),
    "videos": []
}

for item in response_videos["items"]:
    video = {
        "title": item["snippet"]["title"],                       # Titre de la vidéo
        "duration": item["contentDetails"]["duration"],          # Durée au format ISO 8601
        "video_id": item["id"],                                  # ID de la vidéo
        "like_count": item["statistics"].get("likeCount", "0"),  # Nombre de "likes"
        "view_count": item["statistics"].get("viewCount", "0"),  # Nombre de vues
        "published_at": item["snippet"]["publishedAt"],          # Date de publication
        "comment_count": item["statistics"].get("commentCount", "0")  # Nombre de commentaires
    }
    data["videos"].append(video)

# ======================
# 6. Affichage du résultat
# ======================
print(json.dumps(data, indent=4))
