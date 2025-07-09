import os
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
    return redirect(url_for('get_playlists'))

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

    # Step 1: Get user's saved tracks (max 100 for now)
    saved = sp.current_user_saved_tracks(limit=50)
    track_ids = [
        item['track']['id']
        for item in saved['items']
        if item.get('track') and item['track'].get('id')
    ]
    print("length of track_ids")
    print(len(track_ids))

    track_ids = track_ids[:100]





    # Step 2: Get audio features
    features = sp.audio_features(tracks=track_ids[:100])


    # Step 3: Define mood filters
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

    filtered_ids = [f['id'] for f in features if matches_mood(f)]

    if not filtered_ids:
        return "No songs matched your mood. Try again!"

    # Step 4: Create playlist
    user_id = sp.current_user()['id']
    playlist = sp.user_playlist_create(user=user_id, name=f'{mood.capitalize()} Vibes 🎧', public=False)

    # Step 5: Add songs to new playlist
    sp.playlist_add_items(playlist_id=playlist['id'], items=filtered_ids[:100])

    return f"Created playlist: <a href='{playlist['external_urls']['spotify']}' target='_blank'>{playlist['name']}</a>"



#logout endpoint
@app.route('/logout')

def logout():
    session.clear()
    return redirect(url_for('home'))



if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))  # default to 5000 locally
    app.run(host='0.0.0.0', port=port, debug=True)