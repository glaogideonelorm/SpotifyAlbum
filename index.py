from flask import Flask, render_template, request, jsonify, send_from_directory
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import googleapiclient.discovery
from google_auth_oauthlib.flow import InstalledAppFlow
import webbrowser
import os

app = Flask(__name__)

# Spotify API credentials - Replace with your actual credentials
SPOTIPY_CLIENT_ID = '98c0f2d6f63d4c9b8dba8f9b444fd8ec'
SPOTIPY_CLIENT_SECRET = 'ca2daaf0cae04fe098e00057de510106'
SPOTIPY_REDIRECT_URI = 'http://localhost:5000/callback'

# Initialize Spotify API
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID,
                                               client_secret=SPOTIPY_CLIENT_SECRET,
                                               redirect_uri=SPOTIPY_REDIRECT_URI,
                                               scope='user-library-read'))

# YouTube API credentials
CLIENT_SECRETS_FILE = "client_secrets.json"  # Path to your client_secrets.json
SCOPES = ["https://www.googleapis.com/auth/youtube"]

# Function to authenticate YouTube API
def authenticate_youtube_api():
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES)
    credentials = flow.run_local_server(port=8080)
    return googleapiclient.discovery.build("youtube", "v3", credentials=credentials)

# Function to create a playlist on YouTube
def create_playlist(youtube, title):
    request_body = {
        'snippet': {
            'title': title,
            'description': 'Playlist created via script',
            'tags': ['sample', 'playlist'],
            'defaultLanguage': 'en'
        },
        'status': {
            'privacyStatus': 'public'
        }
    }
    response = youtube.playlists().insert(
        part='snippet,status',
        body=request_body
    ).execute()
    return response['id']

# Function to add a video to a playlist on YouTube
def add_video_to_playlist(youtube, video_id, playlist_id):
    add_video_request = youtube.playlistItems().insert(
        part="snippet",
        body={
            'snippet': {
              'playlistId': playlist_id, 
              'resourceId': {
                      'kind': 'youtube#video',
                      'videoId': video_id
              }
            }
        }
    ).execute()

# Function to search and queue songs
def search_and_queue_songs(file_path, youtube):
    playlist_id = create_playlist(youtube, "My Playlist")
    playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}"
    print(f"Playlist created: {playlist_url}")

    with open(file_path, "r") as file:
        song_entries = [line.strip() for line in file]

    if not song_entries:
        print("No song entries found in the file.")
        return

    for entry in song_entries:
        search_response = youtube.search().list(
            q=entry, type="video", part="id,snippet", maxResults=1
        ).execute()

        if "items" in search_response and search_response["items"]:
            video_id = search_response["items"][0]["id"]["videoId"]
            add_video_to_playlist(youtube, video_id, playlist_id)
            print(f"Added to playlist: {entry}")

    webbrowser.open(playlist_url)
    os.remove(file_path)
    print(f"Deleted file: {file_path}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route('/extract')
def extract_album_songs():
    try:
        spotify_link = request.args.get('spotify_link', '')
        if "album" not in spotify_link:
            raise ValueError("Invalid URL. Please provide a valid Spotify album link.")

        album_info = sp.album(spotify_link)
        album_name = album_info['name']
        tracks = album_info['tracks']['items']
        file_name = f"{album_name.replace(' ', '_').lower()}_songs.txt"

        with open(file_name, 'w') as file:
            for track in tracks:
                artist_names = ', '.join(artist['name'] for artist in track['artists'])
                file.write(f"{track['name']} - {artist_names}\n")

        youtube_api = authenticate_youtube_api()
        search_and_queue_songs(file_name, youtube_api)
        return jsonify({"result": f"Songs from album '{album_name}' saved to {file_name}. Check your default web browser."})
    except ValueError as ve:
        return jsonify({"error": str(ve)})
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
