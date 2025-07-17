import os
import re
from flask import Flask, request, redirect, session, url_for, render_template
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import FlaskSessionCacheHandler

#creates the actual web app
app = Flask(__name__)

#used to encrypt session information from users
app.secret_key = os.urandom(64)
#app.config['SECRET KEY'] = os.urandom(64)

#from spotify api website
client_id = '9001e8d19905435598ed117cbb46fd8e'
client_secret = 'ef0ab8129cba4852948fb4c16ea2b47d'
redirect_uri = 'https://moodify-9rar.onrender.com/callback'
scope = 'playlist-read-private user-library-read playlist-modify-private playlist-modify-public'


#manages the session
cache_handler = FlaskSessionCacheHandler(session)

#authetication manager
sp_oauth = SpotifyOAuth(
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri=redirect_uri,
    scope=scope,  
    cache_handler=cache_handler,
    show_dialog=True
)

#spotify client instance
sp = Spotify(auth_manager=sp_oauth)



#we now are going to write out first endpoint
# allows people to log in and see what parts of their data will be acessed
#creating homepage
@app.route('/')
def home():
    #check to see if they are logged in
    if not sp_oauth.validate_token(cache_handler.get_cached_token()):
        #get them to log in
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)
    return redirect(url_for('choose_mood'))

#create endpoint where redirect happens
@app.route('/callback')
def callback():
    sp_oauth.get_access_token(request.args['code'])
    return redirect(url_for('choose_mood'))

#create endpoint for actual task at hand: getting the playlists
@app.route('/get_playlists')
def get_playlists():
    #check to see if they are logged in
    if not sp_oauth.validate_token(cache_handler.get_cached_token()):
        #get them to log in
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)
    
    playlists = sp.current_user_playlists(limit=8)
    playlists_info = [(pl['name'], pl['external_urls']['spotify']) for pl in playlists['items']]
    #playlists_html = '<br>'.join([f'{name}: {url}' for name, url in playlists_info])

    #in order to update flask route to html page
    return render_template('playlists.html', playlists=playlists_info)

#now we're gonna add a new route for mood selection
@app.route('/choose_mood')
def choose_mood():
    return render_template('choose_mood.html')

#this route generates the playlist based on mood selection
@app.route('/generate_playlist', methods=['POST'])
def generate_playlist():
    # Step 0: Create a fresh auth manager and client
    sp_oauth = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=scope,
        cache_handler=FlaskSessionCacheHandler(session)
    )

    token_info = sp_oauth.get_cached_token()
    if not sp_oauth.validate_token(token_info):
        return redirect(sp_oauth.get_authorize_url())

    access_token = token_info['access_token']
    sp = Spotify(auth=access_token)  # THIS is the working client

    # Step 1: Get user's saved tracks
    saved = sp.current_user_saved_tracks(limit=50)
    for item in saved['items']:
        print(item['track']['name'], item['track']['id'])

    # Step 2: Extract and clean track IDs
    track_ids = []
    for item in saved['items']:
        track = item.get('track')
        track_id = track.get('id') if track else None
        if track_id and isinstance(track_id, str):
            cleaned = track_id.strip()
            if len(cleaned) == 22 and re.match(r'^[A-Za-z0-9]+$', cleaned):
                track_ids.append(cleaned)
    track_ids = track_ids[:100]

    print("Cleaned track IDs:", track_ids)
    print("Request URL:", f"https://api.spotify.com/v1/audio-features/?ids={','.join(track_ids)}")

    if not track_ids:
        return "No valid track IDs found."

    # Step 3: Fetch audio features
    def get_audio_features_batch(track_ids):
        features = []
        for i in range(0, len(track_ids), 100):
            batch = track_ids[i:i + 100]
            try:
                batch_features = sp.audio_features(batch)
                features.extend(batch_features)
            except Exception as e:
                print(f"Error fetching audio features for batch {i // 100 + 1}: {e}")
        return features

    features = get_audio_features_batch(track_ids)
    print("Number of audio features fetched:", len(features))
    for f in features[:10]:
        if f:
            print(f"Track ID: {f['id']}, valence: {f['valence']}, energy: {f['energy']}")

    # Step 4: Filter by mood
    mood = request.form.get('mood')
    def matches_mood(f):
        if not f: return False
        if mood == 'happy':
            return f['valence'] > 0.7
        elif mood == 'sad':
            return f['valence'] < 0.4
        elif mood == 'energetic':
            return f['energy'] > 0.7
        elif mood == 'chill':
            return f['energy'] < 0.4 and 0.4 < f['valence'] < 0.7
        return False

    filtered_ids = [f['id'] for f in features if matches_mood(f) and f.get('id')]

    if not filtered_ids:
        return "No songs matched your mood. Try again!"

    # Step 5: Create playlist
    user_id = sp.current_user()['id']
    playlist = sp.user_playlist_create(user=user_id, name=f'{mood.capitalize()} Vibes 🎧', public=False)

    # Step 6: Add tracks to playlist
    try:
        sp.playlist_add_items(playlist_id=playlist['id'], items=filtered_ids[:100])
    except Exception as e:
        return f"Error adding songs: {str(e)}"

    # Step 7: Return success
    return f"""
        <h3>Playlist created!</h3>
        <a href="{playlist['external_urls']['spotify']}" target="_blank">{playlist['name']}</a>
        <br><br>
        <a href="/choose_mood">Make another</a> | <a href="/logout">Logout</a>
    """



#logout endpoint
@app.route('/logout')

def logout():
    session.clear()
    return redirect(url_for('home'))



if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))  # default to 5000 locally
    app.run(host='0.0.0.0', port=port, debug=True)