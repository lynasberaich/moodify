import os
from flask import Flask, request, redirect, session, url_for
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(64)

sp_oauth = SpotifyOAuth(
    client_id=os.getenv("SPOTIPY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
    redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
    scope="user-library-read user-top-read user-read-private"
)

def get_token():
    token_info = session.get('token_info', None)
    if not token_info:
        return None

    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
        session['token_info'] = token_info
    return token_info


@app.route('/')
def login():
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    session['token_info'] = token_info  # ✅ Save token in session
    access_token = token_info['access_token']

    sp = Spotify(auth=access_token)
    user = sp.current_user()
    #return f"Logged in as {user['display_name']}"
    return redirect(url_for('get_playlist', mood='happy'))


@app.route('/get_playlist/<mood>')
def get_playlist(mood):

    #re-autheticate, use a token cache
    token_info = get_token()
    if not token_info:
        return redirect('/')
    
    sp = Spotify(auth=token_info['access_token'])

    test_id = "11dFghVXANMlKmJXsNCbNl"  # This is a known public track (by Daft Punk)
    test_feature = sp.audio_features([test_id])
    print("Test feature:", test_feature)


    #get top 50 tracks
    top_tracks = sp.current_user_top_tracks(limit=20)['items']

    #get audio features for these tracks
    track_ids = [track['id'] for track in top_tracks if track.get('id') is not None]
    track_ids = [tid for tid in track_ids if tid and tid.strip() != ""]
    print("Track IDs:", track_ids)
    features = []
    for tid in track_ids:
        try:
            f = sp.audio_features([tid])[0]
            if f:  # some may be None
                features.append(f)
        except Exception as e:
            print(f"Skipping {tid} due to error:", e)


    #mood rules
    MOOD_RULES = {
        'happy': lambda f: f['valence'] > 0.7 and f['energy'] > 0.7,
        'sad': lambda f: f['valence'] < 0.3 and f['energy'] < 0.3,
        'chill': lambda f: f['valence'] > 0.5 and f['energy'] < 0.5,
        'energetic': lambda f: f['valence'] > 0.6 and f['energy'] > 0.6,
        'romantic': lambda f: f['valence'] > 0.6 and f['danceability'] > 0.6,
    }

    if mood not in MOOD_RULES:
        return f"Unknown mood: {mood}", 400
    
    matched_tracks = []
    for track, feature in zip(top_tracks, features):
        if feature and MOOD_RULES[mood](feature):
            matched_tracks.append({
                'name': track['name'],
                'artist': track['artists'][0]['name'],
                'preview_url': track['preview_url'],
                'external_url': track['external_urls']['spotify']
            })

    return matched_tracks if matched_tracks else f"No tracks found for mood: {mood}", 200

if __name__ == '__main__':
    app.run(debug=True)