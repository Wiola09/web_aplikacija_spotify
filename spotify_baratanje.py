from spotipy.oauth2 import SpotifyOAuth


class SpotifyMoja:
    def create_spotify_oauth(scope, app):
        return SpotifyOAuth(
            client_id=app.config['SPOTIPY_CLIENT_ID'],
            client_secret=app.config['SPOTIPY_CLIENT_SECRET'],
            redirect_uri=app.config['SPOTIPY_REDIRECT_URI'],
            scope=scope
        )

    def sve_playliste(sp):
        """
        dobijanje spiska playlisti
           # 2003-08-12 Billboard 100 33PHqSuB3iMvZbgb4yL6zw
            # 2000-08-12 Billboard 100 55cN2BdISNsfCysrNHGCqf
            # My Playlist #1 63Zz40kyNXuel6nbYLG2q5
        :return:
        """
        # Izlistavanje svih playlista korisnika
        playlists = sp.current_user_playlists()
        liste_recnik = {}
        for playlist in playlists['items']:
            print(playlist['name'], playlist['id'])
            liste_recnik[playlist['name']] = playlist['id']
        return liste_recnik

    def prikaz_pesama_u_playlist_ceo_json(sp, id_liste):
        """
        Izdvojio sam kao poseban metod, zato sto on vraća ceo json, koji posle treba da se sa return jsonify(rezultat)
        renderuje na stranicu, json je poprilicno veli, ali na onovu podtaka iz njega je pravljena metoda
        prikaz_pesama_u_playlist(sp, id_liste)
        :param id_liste:
        :return:
        """
        playlist_id = id_liste
        results = sp.playlist_items(playlist_id)
        return results

    def prikaz_pesama_u_playlist(sp, id_liste):
        """
        koristen za testiranje, finalni proizvod je u funkciji prikaz_pesama_u_playlist_ceo_json
        :param id_liste:
        :return:
        """
        # You should use playlist_items(playlist_id, ..., additional_types=('track',))`  instead playlist_tracks()
        playlist_id = id_liste
        results = sp.playlist_items(playlist_id)
        for item in results['items']:
            track = item['track']
            print(track['name'], track['artists'][0]['name'])
            # items[0].track.name  , za ime track['name']

        pesma_prva = results['items'][0]['track']
        # try kod ne radi, akda se kopira pomocu Chrome ad ona JSON Vier pro, dobije se ovakva putanja

        try:
            pesma_cela = pesma_prva.href
            pesma_deo = pesma_prva.preview_url
            pesma_album_ime = pesma_prva.album.name
            pesma_album_link = pesma_prva.album.external_urls.spotify
            pesma_album_foto = pesma_prva.album.images[0].url
        except:
            print("ipak ovo")
            pesma_cela = pesma_prva['href']
            pesma_cela_bez_aut = pesma_prva["external_urls"]["spotify"]
            pesma_deo = pesma_prva["preview_url"]
            pesma_album_ime = pesma_prva["album"]["name"]
            pesma_album_link = pesma_prva["album"]["external_urls"]["spotify"]
            pesma_album_foto = pesma_prva["album"]["images"][0]["url"]

        print(pesma_cela, "traži token")
        print(pesma_cela_bez_aut, "treba da moze do pemse")
        print(pesma_deo)
        print(pesma_album_ime)
        print(pesma_album_link, "link na spotify ka celom albumu")
        print(pesma_album_foto, " foto kovera 640 x 640")

        return results



# <!--    <hr class="heading">-->
# <!--    <div> <h4> IATA kod {{grad['code']}}, ime grada je {{grad['name']}}, ime grada i države je {{grad['slug_en']}}"</h4>-->
# <!--        <a href="{{ url_for('unesi_grad_u_db', iata_kod_grada=grad['code'], ime_grada=grad['name']) }}" class="button">Dodaj u bazu</a></div>-->
# <!--    <br>-->