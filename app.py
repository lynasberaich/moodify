# import os
# from flask import Flask, request, redirect, session, url_for, render_template, has_request_context
# from spotipy import Spotify
# from spotipy.oauth2 import SpotifyOAuth
# from dotenv import load_dotenv
# from spotipy.cache_handler import FlaskSessionCacheHandler

# load_dotenv()

# app = Flask(__name__)
# #app.secret_key = os.urandom(64)
# #using fixed secret key instead
# app.secret_key = os.getenv("FLASK_SECRET_KEY", "fallback-key")

# # #manages the session
# # cache_handler = FlaskSessionCacheHandler(session)

# # sp_oauth = SpotifyOAuth(
# #     client_id=os.getenv("SPOTIPY_CLIENT_ID"),
# #     client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
# #     redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
# #     scope="user-library-read user-top-read user-read-private"
# # )

# # create these per-request
# def get_auth_manager():
#     if not has_request_context():
#         raise RuntimeError("Tried to access session outside of request context")
    
#     return SpotifyOAuth(
#         client_id=os.getenv("SPOTIPY_CLIENT_ID"),
#         client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
#         redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
#         scope="user-library-read user-top-read user-read-private",
#         cache_handler=FlaskSessionCacheHandler(session),
#         show_dialog=True
#     )



# @app.route('/')
# def home():
#     auth_manager = get_auth_manager()
#     #check to see if they are logged in
#     if not auth_manager.validate_token(auth_manager.cache_handler.get_cached_token()):
#         #get them to log in
#         auth_url = auth_manager.get_authorize_url()
#         return redirect(auth_url)
#     return redirect(url_for('get_playlist', mood="happy"))

# #create endpoint where callback happens
# @app.route('/callback')
# def callback():
#     try:
#         print("🎯 HIT /callback")
#         auth_manager = get_auth_manager()
#         code = request.args.get('code')
#         print("🔑 Got code:", code)

#         token = auth_manager.get_access_token(code)
#         print("✅ Got token:", token)

#         return redirect(url_for('get_playlist', mood="happy"))
#     except Exception as e:
#         print("❌ error in /callback:", e)
#         return "callback failed :(", 500



# @app.route('/get_playlist/<mood>')
# def get_playlist(mood):
#     print("🎵 HIT /get_playlist with mood:", mood)
#     auth_manager = get_auth_manager()
#     #check to see if they are logged in
#     if not auth_manager.validate_token(auth_manager.cache_handler.get_cached_token()):
#         #otherwise get them to log in
#         return redirect(auth_manager.get_authorize_url())
    
#     #then create our instance
#     print("🧠 Building Spotify client...")
#     sp = Spotify(auth_manager=auth_manager)


#     try:
#         # test_id = "11dFghVXANMlKmJXsNCbNl"  # known public track (by Daft Punk)
#         # test_feature = sp.audio_features([test_id])
#         # print("Test feature:", test_feature)


#         #get top 50 tracks
#         top_tracks = sp.current_user_top_tracks(limit=20)['items']
#         print("🎶 Pulled top tracks:", len(top_tracks))

#         #get audio features for these tracks
#         track_ids = [track['id'] for track in top_tracks if track.get('id')]
#         #track_ids = [tid for tid in track_ids if tid and tid.strip() != ""]
#         #print("Track IDs:", track_ids)
#         features = []
#         for tid in track_ids:
#             try:
#                 f = sp.audio_features([tid])[0]
#                 if f:  # some may be None
#                     features.append(f)
#             except Exception as e:
#                 print(f"Skipping {tid} due to error:", e)


#         #mood rules
#         MOOD_RULES = {
#             'happy': lambda f: f['valence'] > 0.7 and f['energy'] > 0.7,
#             'sad': lambda f: f['valence'] < 0.3 and f['energy'] < 0.3,
#             'chill': lambda f: f['valence'] > 0.5 and f['energy'] < 0.5,
#             'energetic': lambda f: f['valence'] > 0.6 and f['energy'] > 0.6,
#             'romantic': lambda f: f['valence'] > 0.6 and f['danceability'] > 0.6,
#         }

#         if mood not in MOOD_RULES:
#             return f"Unknown mood: {mood}", 400
        
#         matched_tracks = []
#         for track, feature in zip(top_tracks, features):
#             if feature and MOOD_RULES[mood](feature):
#                 matched_tracks.append({
#                     'name': track['name'],
#                     'artist': track['artists'][0]['name'],
#                     'preview_url': track['preview_url'],
#                     'external_url': track['external_urls']['spotify']
#                 })

#         return matched_tracks if matched_tracks else f"No tracks found for mood: {mood}", 200
    
#     except Exception as e:
#         print("error in /get_playlist: ", e)
#         return "error loading playlist", 500
    

# @app.route('/ping')
# def ping():
#     return "App is alive!"

# #logout endpoint
# @app.route('/logout')
# def logout():
#     session.clear()
#     return redirect(url_for('home'))

# if __name__ == '__main__':
#     app.run(debug=True)

import os
from flask import Flask, redirect, request, session, url_for, has_request_context
from dotenv import load_dotenv
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import FlaskSessionCacheHandler

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "fallback-key")

from flask import has_request_context

def get_auth_manager():
    try:
        if not has_request_context():
            print("🚫 No request context — cannot use session")
            return None

        return SpotifyOAuth(
            client_id=os.getenv("SPOTIPY_CLIENT_ID"),
            client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
            redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
            scope="user-library-read user-top-read user-read-private",
            cache_handler=FlaskSessionCacheHandler(session),
            show_dialog=True
        )
    except Exception as e:
        print("❌ Failed to create SpotifyOAuth:", e)
        return None



@app.route("/")
def home():
    print("🔁 HIT /")
    auth_manager = get_auth_manager()
    if not auth_manager.validate_token(auth_manager.cache_handler.get_cached_token()):
        return redirect(auth_manager.get_authorize_url())
    return redirect(url_for("profile"))

@app.route("/callback")
def callback():
    print("🎯 HIT /callback")

    try:
        code = request.args.get("code")
        print("🔑 Received code:", code)

        auth_manager = get_auth_manager()

        if not auth_manager:
            print("⚠️ Auth manager is None — request context issue?")
            return "Failed to initialize SpotifyOAuth", 500

        token_info = auth_manager.get_access_token(code)
        print("✅ Token info received:", token_info)

        return redirect(url_for("profile"))

    except Exception as e:
        print("❌ Exception in /callback:", e)
        return "Callback failed", 500


@app.route("/profile")
def profile():
    print("🧠 HIT /profile")
    auth_manager = get_auth_manager()
    if not auth_manager.validate_token(auth_manager.cache_handler.get_cached_token()):
        return redirect(auth_manager.get_authorize_url())
    
    sp = Spotify(auth_manager=auth_manager)
    user = sp.current_user()
    return {
        "display_name": user.get("display_name"),
        "id": user.get("id"),
        "email": user.get("email")
    }

@app.route("/ping")
def ping():
    return "pong"

