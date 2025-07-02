import os
from flask import Flask, request, redirect, session, url_for
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
from spotipy.cache_handler import FlaskSessionCacheHandler

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(64)

#manages the session
cache_handler = FlaskSessionCacheHandler(session)

sp_oauth = SpotifyOAuth(
    client_id=os.getenv("SPOTIPY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
    redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
    scope="user-library-read user-top-read user-read-private"
)



@app.route('/')
def home():
    #check to see if they are logged in
    if not sp_oauth.validate_token(cache_handler.get_cached_token()):
        #get them to log in
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)
    return redirect(url_for('get_playlist', mood="happy"))

#create endpoint where redirect happens
@app.route('/callback')
def callback():
    sp_oauth.get_access_token(request.args['code'])
    return redirect(url_for('get_playlist', mood="happy"))


@app.route('/get_playlist/<mood>')
def get_playlist(mood):

    #check to see if they are logged in
    if not sp_oauth.validate_token(cache_handler.get_cached_token()):
        #get them to log in
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)
    
    sp = Spotify(auth_manager=sp_oauth, cache_handler=cache_handler)

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

@app.route('/ping')
def ping():
    return "App is alive!"

#logout endpoint
@app.route('/logout')

def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)