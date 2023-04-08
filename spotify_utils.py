import spotipy
from spotipy.oauth2 import SpotifyOAuth


class SpotifyMoja2(spotipy.Spotify):
    def __init__(self, scope, app):
        auth_manager = SpotifyOAuth(
            client_id=app.config['SPOTIPY_CLIENT_ID'],
            client_secret=app.config['SPOTIPY_CLIENT_SECRET'],
            redirect_uri=app.config['SPOTIPY_REDIRECT_URI'],
            scope=scope
        )
        self.auth_manager = auth_manager
        super().__init__(auth_manager=auth_manager)
        self.logger = app.logger  # dodajte ovu liniju kako biste povezali logger iz vaše klase s
        # loggerom u Flask aplikaciji

        # self.logger.info(f"Using logger: {self.logger.name}")   # linija za test logera

    def get_auth_url(self):
        return self.auth_manager.get_authorize_url()

    def get_cached_token(self):
        return self.auth_manager.get_cached_token()

    def pormeni_poziciju_pesme(self, playlist_id, range_start):
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
        self.playlist_reorder_items(playlist_id, range_start=(int(range_start) - 1), insert_before=4, range_length=1,
                                    snapshot_id=None)

    def sve_playliste(self):
        """
        dobijanje spiska playlisti
           # 2003-08-12 Billboard 100 33PHqSuB3iMvZbgb4yL6zw
            # 2000-08-12 Billboard 100 55cN2BdISNsfCysrNHGCqf
            # My Playlist #1 63Zz40kyNXuel6nbYLG2q5
        :return:
        """
        # Izlistavanje svih playlista korisnika
        playlists = self.current_user_playlists()
        liste_recnik = {}
        for playlist in playlists['items']:
            print(playlist['name'], playlist['id'])
            liste_recnik[playlist['name']] = playlist['id']
        return liste_recnik

    def current_user_playlists(self, limit=50, offset=0):
        """
        Override spotipy.Spotify.current_user_playlists() method to return a dictionary with playlist names and ids
        """
        # response = self._get('me/playlists', limit=limit, offset=offset)
        # playlists = response['items']
        # while response['next']:
        #     response = self._get(response['next'])
        #     playlists.extend(response['items'])
        playlists = super().current_user_playlists(limit=limit, offset=offset)['items']
        liste_recnik = {}
        for playlist in playlists:
            liste_recnik[playlist['name']] = playlist['id']
        return liste_recnik

    def create_playlist_and_add_songs(self, song_uris):
        user_id = self.current_user()["id"]
        date = "20111-08-12"

        playlist = self.user_playlist_create(user=user_id, name=f"{date} Billboard 100", public=False)
        self.logger.info(f"Created new playlist: {playlist['id']}")

        self.playlist_add_items(playlist_id=playlist["id"], items=song_uris)
        self.logger.info(f"Added {len(song_uris)} songs to the playlist.")

        print("Care dodao !!!")

    def pronadji_pesme_iz_liste(self):
        date = "2003-08-12"
        song_names = ['Incomplete', 'Bent', "It's Gonna Be Me", "Jumpin', Jumpin'"]
        song_uris = []
        year = date.split("-")[0]
        broj_preskocene = 0
        for song in song_names:
            result = self.search(q=f"track:{song} year:{year}", type="track")
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

    # Primer za overide, ali sam se ipak odlucio da ga ne pravim, vec da hvatam u kodu sa try except
    # def playlist_remove_all_occurrences_of_items(self, playlist_id, items, snapshot_id=None):
    #     """
    #     Override spotipy.Spotify.playlist_remove_all_occurrences_of_items() method to remove all occurrences of the
    #     given tracks/episodes from the given playlist
    #     """
    #     try:
    #         super().playlist_remove_all_occurrences_of_items(playlist_id=playlist_id, items=[items],
    #                                                          snapshot_id=snapshot_id)
    #         print("obrisana")
    #     except:
    #         print("greska")
