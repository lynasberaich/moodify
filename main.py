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
    #check to see if they are logged in
    if not sp_oauth.validate_token(cache_handler.get_cached_token()):
        #get them to log in
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)

    mood = request.form.get('mood')
    # token_info = cache_handler.get_cached_token()
    # sp = Spotify(auth=token_info['access_token']) <- we already did this globally i think

    # Step 1: Get user's saved tracks
    saved = sp.current_user_saved_tracks(limit=50)

    # Step 2: Extract and clean track IDs
    track_ids = []
    for item in saved['items']:
        track = item.get('track')
        track_id = track.get('id') if track else None
        if track_id and isinstance(track_id, str):
            cleaned = track_id.strip()
            if len(cleaned) == 22 and re.match(r'^[A-Za-z0-9]+$', cleaned):
                track_ids.append(cleaned)


    track_ids = track_ids[:100]  # Max 100 allowed

    # DEBUG: View cleaned track IDs in logs
    print("Cleaned track IDs:", track_ids)
    for tid in track_ids:
        if ":" in tid:
            print("❌ Colon found in:", tid)
    print("Track IDs (clean):", track_ids)
    print("Request URL:", f"https://api.spotify.com/v1/audio-features/?ids={','.join(track_ids)}")

    if not track_ids:
        return "No valid track IDs found."

    # DEBUG (optional — will show in Render logs)
    print("Track IDs to send:", track_ids)

    # Step 3: Call audio_features safely
    try:
        features = sp.audio_features(tracks=track_ids)
    except Exception as e:
        return f"Spotify API error: {str(e)}"

    # Step 4: Define mood filtering
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

    # Step 5: Filter and prepare track list
    filtered_ids = [f['id'] for f in features if matches_mood(f) and f.get('id')]

    if not filtered_ids:
        return "No songs matched your mood. Try again!"

    # Step 6: Create a new playlist
    user_id = sp.current_user()['id']
    playlist = sp.user_playlist_create(user=user_id, name=f'{mood.capitalize()} Vibes 🎧', public=False)

    # Step 7: Add filtered songs to the playlist
    try:
        sp.playlist_add_items(playlist_id=playlist['id'], items=filtered_ids[:100])
    except Exception as e:
        return f"Error adding songs: {str(e)}"

    # Step 8: Return success message
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