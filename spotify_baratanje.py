
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

    def pronadji_pesme_iz_liste(sp):
        date = "2003-08-12"
        song_names = ['Incomplete', 'Bent', "It's Gonna Be Me", "Jumpin', Jumpin'"]
        song_uris = []
        year = date.split("-")[0]
        broj_preskocene = 0
        for song in song_names:
            result = sp.search(q=f"track:{song} year:{year}", type="track")
            # print(result)
            try:
                uri = result["tracks"]["items"][0]["uri"]
                song_uris.append(uri)
            except IndexError:
                broj_preskocene += 1
                print(f"{broj_preskocene}. {song} doesn't exist in Spotify. Skipped.")

        # with open("text2.txt", "a") as f:
        #     for i in song_uris:
        #         f.write(i + "\n")
        return song_uris

    def kreiraj_pl_i_dodaj_pesme(sp, song_uris):
        """
        Kreira play listu i doaje pesme
        """
        user_id = sp.current_user()["id"]
        date = "2007-08-12"
        playlist = sp.user_playlist_create(user=user_id, name=f"{date} Billboard 100", public=False)
        print(playlist)

        sp.playlist_add_items(playlist_id=playlist["id"], items=song_uris)

        print("Care dodao !!!")

    def obrisi_pesmu(sp, id_liste, id_pesme):
        """
        playlist_remove_all_occurrences_of_items(playlist_id, items, snapshot_id=None)
        Removes all occurrences of the given tracks/episodes from the given playlist

        Parameters:
        playlist_id - the id of the playlist
        items - list of track/episode ids to remove from the playlist
        :param id_liste:
        :param id_pesme:
        :return:
        """
        try:
            sp.playlist_remove_all_occurrences_of_items(playlist_id=id_liste, items=[id_pesme])
            print("obrisana")
        except:
            print("greska")
# todo: doraditi metod, da korisnik unese zeljenu poziciju
    def pormeni_poziciju_pesme(sp, playlist_id, range_start):
        """
            playlist_reorder_items(playlist_id, range_start, insert_before, range_length=1, snapshot_id=None)
            Reorder tracks in a playlist

            Parameters:
            playlist_id - the id of the playlist
            range_start - the position of the first track to be reordered
            range_length - optional the number of tracks to be reordered
            (default: 1)
            insert_before - the position where the tracks should be
            inserted
            snapshot_id - optional playlist’s snapshot ID
        """
        sp.playlist_reorder_items(playlist_id, range_start=(int(range_start) - 1), insert_before=5, range_length=1,
                                  snapshot_id=None)

