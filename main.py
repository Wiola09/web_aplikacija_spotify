import os
import time
import requests
import json
import http.client
from flask import Flask, render_template, redirect, url_for, request, flash, current_app, jsonify, session
from flask_bootstrap import Bootstrap
from werkzeug.security import check_password_hash
from flask_login import LoginManager, login_user, current_user, login_required, logout_user
import spotipy
import logging
from logging.handlers import RotatingFileHandler
from spotipy.oauth2 import SpotifyOAuth

# # Deo koji se odnosi na moje fajlove
from data_manager import db, DataManager, UserData, UserSema
from forms_view import UnesiPodateZaPretraguForm, DodajPesmu, DodajListu
from spotify_baratanje import SpotifyMoja
from spotify_utils import SpotifyMoja2
from scraping_top_100_utils import Top100Movies

APP_SECRET_KEY = os.getenv("APP_SECRET_KEY", "default_value")

app = Flask(__name__)
app.config['SECRET_KEY'] = APP_SECRET_KEY
app.config['SESSION_COOKIE_SECURE'] = True
Bootstrap(app)

# Deo vezan za spotify
SPOTIPY_CLIENT_ID = os.environ["SPOTIPY_CLIENT_ID"]
SPOTIPY_CLIENT_SECRET = os.environ["SPOTIPY_CLIENT_SECRET"]
SPOTIPY_REDIRECT_URI = os.environ["SPOTIPY_REDIRECT_URI"]
app.config["SPOTIPY_CLIENT_ID"] = SPOTIPY_CLIENT_ID
app.config["SPOTIPY_CLIENT_SECRET"] = SPOTIPY_CLIENT_SECRET
app.config["SPOTIPY_REDIRECT_URI"] = SPOTIPY_REDIRECT_URI

# Key https://apilayer.com/marketplace/spotify-api
API_LAYER_API_KEY = os.environ["API_LAYER_API_KEY"]

# https://pypi.org/project/lyricsgenius/
# https://docs.genius.com/#/getting-started-h1
GENIUS_ACCESS_TOKEN = os.environ["GENIUS_ACCESS_TOKEN"]

# CREATE DATABASE
# Prva linija mi javlja gresku, problem je bio sto sam dodao env vrednost DATABASE_URL1, pa je on nalazi, ne treba je
# dodavati, jer je ence naci pa koristi sqlite
try:
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL1", 'sqlite:///kalup-flask.db')
except:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///new-flight-collection2.db'
    print("izabrao rezervu")

# Optional: But it will silence the deprecation warning in the console.
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db.init_app(app)  # vidi komentar u "data_manager.py"

# deo logovanje regisrovanje
""" The login manager contains the code that lets your application and Flask-Login work together, such as how to load a 
user from an ID, where to send users when they need to log in, and the like.
Once the actual application object has been created, you can configure it for login with:"""
login_manager = LoginManager()
login_manager.init_app(app)

""" The above code allows the app and login manager to work together. User_id allows to display unique data for 
each user at a website (like account info, past purchases, carts, etc.)"""

# bez app_context() javlja gresku, mozda je do verzija Flask-SQLAlchemy==3.0.2
with app.app_context():
    db.create_all()

# Konfigurisanje logging-a
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log_handler = RotatingFileHandler(filename="app.log", maxBytes=1000000, backupCount=10)
log_handler.setLevel(logging.DEBUG)
app.logger.setLevel(logging.DEBUG)
log_handler.setFormatter(formatter)
app.logger.addHandler(log_handler)
# spotify = SpotifyMoja2('playlist-read-private', app)


def loger_debug():
    # Ako sada želite vidjeti koje druge razine logiranja su uključene i koje
    # su isključene, možete koristiti sljedeći kod:
    print("Level of app.logger:", app.logger.getEffectiveLevel())
    # Provjeri status loggera
    if app.logger.disabled:
        print("Logger isključen!")
    else:
        print("Logger uključen!")

    # Provjeri razinu efektivne razine loggera
    if app.logger.getEffectiveLevel() == logging.DEBUG:
        print("Debug razine loggera uključena!")
    else:
        print("Debug razine loggera isključena!")
    print(app.debug)
    app.debug = True
    print(app.debug)
    # Provjeri razinu efektivne razine loggera
    if app.logger.getEffectiveLevel() == logging.DEBUG:
        print("Debug razine loggera uključena!")
    else:
        print("Debug razine loggera isključena!")
    # Provjeri logger
    app.logger.debug("Poruka za debug")


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(UserSema, int(user_id))


# TODO uraditi reformat da se ne koristi direkno klasa DB vec UserData

@app.route('/favicon.ico')
def favicon():
    """
    Morao sam dodati ovu funkciju jer izgleda da mi base.html nije bio u kontekstu, pa url_for nije radio,
     problem je nastao kada sam dodao footer.html i ejdnostavno favicon nije mogao da bude nađen
    :return: file favicon.ico
    """
    return redirect(url_for('static', filename='images/favicon.ico'))


@app.route('/pocetak')
def pocetak():
    """ Početna stranica daje dugmad za logovanjE i registrovanje
    :return: prikazuje html stranicu "pocetak.html"
    """
    return render_template("pocetak.html")


@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')
        user_object = UserData.pretrazi_db_po_korisniku(UserData, vrednost_za_pretragu=email)
        # TODO

        if not user_object:
            # metod flash je iz flaska, dodat kod i u *.html stranici
            flash("That email does not exist, please register.")
            return redirect(url_for('register'))

        # Password incorrect
        # Check stored password hash against entered password hashed.
        elif not check_password_hash(user_object.password, password):
            # metod flash je iz flaska, dodat kod i u *.html stranici
            flash('Password incorrect, please try again.')
            return redirect(url_for('login'))

        # Email exists and password correct
        else:  # If the user has successfully logged in or registered, you need to use the login_user() function to
            # authenticate them.
            login_user(user_object)
            return redirect(url_for('spotify_podaci_posle_auth',
                                    name=current_user.name,
                                    logged_in=current_user.is_authenticated))

    return render_template("login.html")


@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        # Predlog od codeGPT :
        try:
            user_object = UserData.pretrazi_db_po_korisniku(UserData, vrednost_za_pretragu=email)
            if user_object:
                flash("You've already signed up with that email, log in instead!")
                return redirect(url_for('login'))
            else:
                UserData(
                    name=name,
                    email=email,
                    password=password,
                ).add_user()
                user = UserSema.query.filter_by(email=email).first()

        except:
            db.session.rollback()
            user = None
            print(user, "hvata ovaj")
            # rukujte s pogreškom na odgovarajući način
        finally:
            db.session.close()

        # TODO uraditi reformat da se ne koristi direkno klasa DB vec UserData
        """ Kada korisnik pošalje podatke za prijavu (npr. korisničko ime i lozinku), obično se ti podaci proveravaju u 
        bazi podataka kako bi se utvrdilo da li su validni. Ako su podaci validni, korisnik se "autentikuje" 
        (authenticate), što znači da se postavlja current_user objekat na instancu User klase koja predstavlja 
        prijavljenog korisnika.U Flasku se ovo obično radi pomoću login_user() funkcije, koja prima User objekat kao 
        argument i postavlja current_user na taj objekat."""
        login_user(user)
        print()

        return redirect(url_for("pocetna_aplikacija", name=current_user.name, logged_in=current_user.is_authenticated))

    return render_template("register.html")


@app.route('/logout')
def logout():
    print(current_user, "pre logout")
    logout_user()
    print(current_user, "posle logout")
    return redirect(url_for('pocetak', logged_in=current_user.is_authenticated))


@app.route('/pocetna_aplikacija', methods=["GET", "POST"])
@login_required
def pocetna_aplikacija():
    return "Zdravo Svete"


@app.route('/')
def pocetak_spotify_auth_vracanje_linka():
    """
    Kada se radi autentifikacija, dobija se auth_url koja mora da se unese u python kod,
    ovde tor adim preko spotify_callback() funkcije. Ukoliko nije korisnik ulogovan na spotify,
    traži da se uloguje
    :return:
    """
    scope = 'playlist-read-private'
    sp_oauth = SpotifyMoja2(scope=scope, app=app)
    auth_url = sp_oauth.get_auth_url()
    # print(auth_url)
    return redirect(auth_url)


@app.route('/spotify_callback')
def spotify_callback():
    # ovde mi ne sme biti dva pojma u scope !!!, nije gteo da se dobije token
    scope = 'playlist-read-private'
    sp_oauth = SpotifyMoja2(scope=scope, app=app)
    session.pop('token_info', None)
    token_info = sp_oauth.get_cached_token()
    print(token_info, "ovde bi morao biti")
    session["token_info"] = token_info
    session.modified = True  # dodajemo ovde da bismo osigurali da se promene u sesiji sačuvaju
    return redirect(url_for('pocetak'))
    # return redirect(url_for('spotify_podaci_posle_auth', logged_in=current_user.is_authenticated))


def playlist_cover_image(playlist_id):
    """
    Funkcija se prosledjuje na HTML i poziva iz HTML-a

    :param playlist_id: iz HTML dobija vrednost
    :return: url do slike
    """
    sp = SpotifyMoja2(scope='playlist-read-private', app=app)
    try:
        url_to_playlist_cover_image = sp.playlist_cover_image(playlist_id)
        url_to_playlist_cover_image = url_to_playlist_cover_image[1]['url']
        # Ovako izglea rezultat
        rezultat = [{'height': 640,
                     'url': 'https://mosaic.scdn.co/640/ab67616d0000b2732bd281188f485ea182f3bd84ab67616d0000b273c558456b314a72d2593bf45dab67616d0000b273cb31e578d052ea8ff425dc5aab67616d0000b273d0d7dbbbb9ee8980315ea58b',
                     'width': 640},
                    {'height': 300,
                     'url': 'https://mosaic.scdn.co/300/ab67616d0000b2732bd281188f485ea182f3bd84ab67616d0000b273c558456b314a72d2593bf45dab67616d0000b273cb31e578d052ea8ff425dc5aab67616d0000b273d0d7dbbbb9ee8980315ea58b',
                     'width': 300},
                    {'height': 60,
                     'url': 'https://mosaic.scdn.co/60/ab67616d0000b2732bd281188f485ea182f3bd84ab67616d0000b273c558456b314a72d2593bf45dab67616d0000b273cb31e578d052ea8ff425dc5aab67616d0000b273d0d7dbbbb9ee8980315ea58b',
                     'width': 60}]
    except:
        url_to_playlist_cover_image = "Nema cover image"

    # print(url_to_playlist_cover_image)
    return url_to_playlist_cover_image


@app.route('/obrisati_listu', methods=['POST'])
def obrisati_listu():
    lista_za_brisanje = request.form['lista_za_brisanje']
    sp = SpotifyMoja2(scope='playlist-read-private', app=app)
    sp.current_user_unfollow_playlist(lista_za_brisanje)
    flash(f"Lista je uspešno obrisana", category='success')
    return redirect(url_for('spotify_podaci_posle_auth'))


@app.route('/spotify_podaci_posle_auth')
def spotify_podaci_posle_auth():
    token_info = session.get("token_info", None)
    if not token_info:
        print("Nema token_info")
        return redirect('/pocetak_spotify_auth_vracanje_linka')
    sp = SpotifyMoja2(scope='playlist-read-private', app=app)

    # pozivam metod iz moje klase, Override spotipy.Spotify.current_user_playlists() method
    liste_recnik = sp.current_user_playlists()
    return render_template("prikaz_playlista_korisnika.html",
                           liste=liste_recnik,
                           playlist_cover_image=playlist_cover_image, name=current_user.name,
                                    logged_in=current_user.is_authenticated)
    return jsonify(liste_recnik)  # vraca kao json stranicu, ali samo imena lista sa njihovim id
    odabrana_lista = '2003-08-12 Billboard 100'

@app.route('/prikazi_pesme_sa_playliste')
def prikazi_pesme_sa_playliste():
    sp = SpotifyMoja2(scope='playlist-read-private', app=app)
    playlist_id = request.args.get('playlist_id')
    playlist_name = request.args.get('playlist_name')
    try:
        rezultat = sp.playlist_items(playlist_id)
    except:
        return "Ne postoji lista"
    # return jsonify(rezultat['items'][0])  # Kod vraca JSON podatke i samo ejdnoj pesmi
    return render_template("prikaz_pesama_playlista.html", pesme=rezultat['items'], lista=playlist_name, playlist_id=playlist_id, name=current_user.name,
                                    logged_in=current_user.is_authenticated)

@app.route('/prikazi_tekst_pesme')
def prikazi_tekst_pesme():
    """
    Uradio pretplatu na apilayer Spotify API
    Koristi https://apilayer.com/marketplace/spotify-api , pa live demo

    Ima 500 mesaceno besplatnih zahteva
    :return:
    """
    song_id = request.args.get('song_id')

    url = f"https://api.apilayer.com/spotify/track_lyrics?id={song_id}"

    payload = {}
    headers = {
        "apikey": API_LAYER_API_KEY
    }

    response = requests.request("GET", url, headers=headers, data=payload)
    status_code = response.status_code
    print(status_code)
    result = response.text
    try:
        response_dict = json.loads(response.text)
        test = response_dict["lyrics"]["lines"][0]['words']
        print(test)

        return render_template("prikaz_tekst_pesme.html", pesma=response_dict["lyrics"]["lines"])
    except:
        return "Nema teksta za pesmu"
    return jsonify(response_dict)


globalna_pesme_pretrage = []
globalna_song_uris = []


@app.route('/genius_direktno')
def genius_direktno():
    umetnik = request.args.get('umetnik')
    naziv_pesme = request.args.get('naziv_pesme')

    GENIUS_ACCESS_TOKEN = os.environ["GENIUS_ACCESS_TOKEN"]

    tip_zahteva = "/songs/7234505"

    """
    # !!! https://docs.genius.com/#songs-h2
    # Prikaz podataka o pesmi sa ID npr. "7234505"
    Songs
    A song is a document hosted on Genius. It's usually music lyrics.
    
    Data for a song includes details about the document itself and information about all the referents that are
     attached to it, including the text to which they refer.
    GET /songs/:id
    api.genius.com/songs/7234505
    """
    tip_zahteva = "/search?q=Toma Zdravkovic"
    tip_zahteva = "/search?q=Brena"
    tip_zahteva = f"/search?q={naziv_pesme}"
    tip_zahteva_with_br = tip_zahteva.replace(' ', '%20')
    tip_zahteva = tip_zahteva_with_br

    """
    Search
    The search capability covers all content hosted on Genius (all songs).
    GET /search
    Search documents hosted on Genius.
    
    q	The term to search for

    """
    # tip_zahteva =  "/artists/457175"

    print(tip_zahteva)
    # konekcija sa genius
    conn = http.client.HTTPSConnection("api.genius.com")
    payload = ''
    headers = {
        'Authorization': f'Bearer {GENIUS_ACCESS_TOKEN}'
    }
    conn.request("GET", f"{tip_zahteva}", payload, headers)
    res = conn.getresponse()
    data = res.read()
    # Pretvaranje u recnik
    response_dict = json.loads(data.decode("utf-8"))

    # testiranje odogovra
    print(data.decode("utf-8"))
    print(type(data.decode("utf-8")))
    print(type(response_dict))

    # Za tip zahteva tip_zahteva = "/songs/7234505"
    # yu_tube = response_dict["response"]["song"]["media"][0]["url"]
    def pretraga_po_tekstu():
        # Za tip_zahteva = "/search?q=Brena" , stampa umetnika i pesmu
        umetnici = response_dict["response"]["hits"]
        for umetnik in umetnici:
            print(umetnik["result"]["artist_names"], umetnik["result"]["primary_artist"]["api_path"], umetnik["result"]["full_title"], umetnik["result"]["id"])
    pretraga_po_tekstu()
    # return redirect(yu_tube)
    return jsonify(response_dict)

@app.route('/prikazi_tekst_pesme_genius')
def prikazi_tekst_pesme_genius():
    umetnik = request.args.get('umetnik')
    naziv_pesme = request.args.get('naziv_pesme')
    import lyricsgenius as lyricsgenius
    print(umetnik)
    print(naziv_pesme)

    # If you don't pass a token to the Genius class, lyricsgenus will look for an environment variable called
    # GENIUS_ACCESS_TOKEN and attempt to use that for authentication.
    genius = lyricsgenius.Genius(GENIUS_ACCESS_TOKEN)
    artist = genius.search_artist(umetnik, max_songs=3, sort="title")
    try:
        print(artist.songs)
    except:
        pass


    genius.remove_section_headers = True
    try:
        # song = genius.search_song(naziv_pesme, artist.name)
        # ne koristim vise rezultat pretarge genius.search_artist, vec direktno pisem umetnika
        song = genius.search_song(naziv_pesme, umetnik)
        # time.sleep(5)
        print(song.lyrics)
        lyrics_with_br = song.lyrics.replace('\n', '<br>')
        return render_template('genius_prikaz_tekst_pesme.html', lyrics=lyrics_with_br, pesma=naziv_pesme, izvodjac=umetnik)
    except:
        return "Nema teksta za pesmu"


@app.route('/pronadji_pesme_i_napravi_listu')
def pronadji_pesme_i_napravi_listu():
    """
    Pronalazi pemse iz liste, i kreira sa njima novu PL,
     TODO: Ispisati broj dodatih pesama i dati url sa top 100
    :return:
    """
    godina = request.args.get('datum')
    token_info = session.get("token_info", None)
    if not token_info:
        print("Nema token_info")
        return redirect('/pocetak_spotify_auth_vracanje_linka')

    sp = SpotifyMoja2(scope='playlist-read-private', app=app)
    objekat_pretraga_pesama = Top100Movies()
    lista_pesama, billboard_url = objekat_pretraga_pesama.lista_top_100_pesama(godina=godina)
    # print(lista_pesama)
    song_uris, pesme = sp.pronadji_pesme_iz_liste(lista_pesama)
    # return jsonify(pesme[0])
    playlist_id = ""
    global globalna_pesme_pretrage
    global globalna_song_uris
    globalna_pesme_pretrage=pesme
    globalna_song_uris = song_uris
    return render_template("prikaz_rezultaat_pretrage.html", pesme=globalna_pesme_pretrage, playlist_id=playlist_id, top100="top100")
    # todo preimenovati funkciju i ovaj deo ispod je prebacen u obrada_rezultata_top100_i_kreiranje_pl
    dodat_broj_pesama, nova_play_lista = sp.create_playlist_and_add_songs(song_uris, date=godina)
    flash(f"Kreirana je nova play lista '{nova_play_lista}' sa {dodat_broj_pesama} pesama za rang listu po 'BILLBOARD HOT 100 LIST', orginalnu top listu možete pogledati na <a href='{billboard_url}'>web stranici</a>", category='success')
    return redirect(url_for("spotify_podaci_posle_auth", billboard_url=billboard_url))


@app.route('/kreiraj_praznu_listu', methods=["GET", "POST"])
def kreiraj_praznu_listu():
    sp = SpotifyMoja2(scope='playlist-read-private', app=app)

    forma = DodajListu()
    if forma.validate_on_submit():
        naziv_liste = forma.naziv_liste.data

        # Nalazim vrednost playlist_id na osnovu imena liste
        playlists = sp.current_user_playlists()
        key_lista = [i for i in playlists if i == naziv_liste]
        try:
            playlist_id = key_lista[0]
        except:
            playlist_id = None
        if playlist_id:
            flash(
                f"Play lista '{naziv_liste}' vec postoji",
                category='danger')
        else:
            user_id = sp.current_user()["id"]
            playlist = sp.user_playlist_create(user=user_id, name=naziv_liste, public=False)
            playlist_id = playlist["id"]
            playlist_name = playlist['name']
            rezultat = sp.playlist_items(playlist_id)
            flash(
                f"Kreirana je prazna nova play lista '{naziv_liste}'",
                category='success')
        try:
            return render_template("prikaz_pesama_playlista.html", pesme=rezultat['items'], lista=playlist_name,
                               playlist_id=playlist_id)
        except:
            return redirect(url_for('spotify_podaci_posle_auth'))


    return render_template("forma_pretraga.html", form=forma)


@app.route('/obrada_rezultata_top100_i_kreiranje_pl', methods=["GET", "POST"])
def obrada_rezultata_top100_i_kreiranje_pl():

    # todo resiti prebacivanje BILLBOARD HOT 100 LIST linka i godine za naziv PL
    global globalna_pesme_pretrage
    global globalna_song_uris

    if request.method == 'POST':
        # kreira play listu
        sp = SpotifyMoja2(scope='playlist-read-private', app=app)
        dodat_broj_pesama, nova_play_lista = sp.create_playlist_and_add_songs(globalna_song_uris, date="2044")

        flash(
            f"Kreirana je nova play lista '{nova_play_lista}' sa {dodat_broj_pesama} pesama za rang listu po 'BILLBOARD HOT 100 LIST', orginalnu top listu možete pogledati na <a href='{1}'>web stranici</a>",
            category='success')
        return redirect(url_for("spotify_podaci_posle_auth", billboard_url="test"))
        # return render_template("prikaz_rezultaat_pretrage.html", pesme=globalna_pesme_pretrage)

    range_start = request.args.get('range_start')
    premesti_na_prvu = request.args.get('izvrsi_premestanje_na_prvu_poziciju')
    # Logika za premestanje odabrane pesme na prvu poziciju, tj. zamenu pozicija
    if premesti_na_prvu:
        staro_uri_prvo_mesto = globalna_song_uris[0]
        globalna_song_uris[0] = globalna_song_uris[int(range_start) - 1]
        globalna_song_uris[int(range_start) - 1] = staro_uri_prvo_mesto
        staro_prvo_mesto = globalna_pesme_pretrage[0]
        globalna_pesme_pretrage[0] = globalna_pesme_pretrage[int(range_start) - 1]
        globalna_pesme_pretrage[int(range_start) - 1] = staro_prvo_mesto
        flash(f"Zamenjene su pozicijeje pesama, izabrana presma je postavljena na prvo mesto liste", category='success')
        return render_template("prikaz_rezultaat_pretrage.html", pesme=globalna_pesme_pretrage, top100="top100")

    # Uzimanje indeksa preko pritiska dugmeta "Ukloni pesmu" na stranici "prikaz_rezultaat_pretrage.html",
    # umanjivanje za jedan i brisanje te pesme iz liste
    # print(range_start, "brisi indeks")
    del globalna_pesme_pretrage[int(range_start) - 1]
    del globalna_song_uris[int(range_start) - 1]
    flash(f"Izabrana pesma je obrisana sa liste", category='success')
    return render_template("prikaz_rezultaat_pretrage.html", pesme=globalna_pesme_pretrage, top100="top100")

@app.route('/pronadji_pesmu', methods=["GET", "POST"])
def pronadji_pesmu():
    # todo napraviti zastitu da se ne dodaju iste pesme u istu listu
    playlist_id = request.args.get('playlist_id')
    forma = DodajPesmu()
    sp = SpotifyMoja2(scope='playlist-read-private', app=app)
    if forma.validate_on_submit():
        song_name = forma.track.data
        song_artist = forma.artist.data
        song_year = forma.year.data
        result = sp.search(q=f"track:{song_name} artist:{song_artist}", type="track")
        print(result)
        if len(result["tracks"]['items']) == 0:
            print("duzina pretrage je nula")
            result = sp.search(q=f"track:{song_name}", type="track")
            flash(
                f"Nema rezultata pretrage za unete podatke",
                category='danger')
        return render_template("prikaz_rezultaat_pretrage.html",
                               pesme=result["tracks"]['items'],
                               playlist_id=playlist_id,
                               pronadji_pesmu="pronadji_pesmu")
    return render_template("forma_nova_pesma_pretraga.html", form=forma, playlist_id=playlist_id)
    return jsonify(result)


@app.route('/obrisi_pesmu')
def obrisi_pesmu():
    playlist_id = request.args.get('playlist_id')
    song_id = request.args.get('song_id')
    playlist_name = request.args.get('playlist_name')
    sp = SpotifyMoja2(scope='playlist-read-private', app=app)

    # Nalazim vrednost imena liste na osnovu playlist_id
    playlists = sp.current_user_playlists()
    key_lista = [i for i in playlists if playlists[i] == playlist_id]
    playlist_name = key_lista[0]

    try:
        sp.playlist_remove_all_occurrences_of_items(playlist_id=playlist_id, items=[song_id])
        print("Pesma uspešno obrisana iz liste.")
    except spotipy.SpotifyException as e:
        print("Greška prilikom brisanja pesme iz liste: {}".format(e))

    return redirect(url_for("prikazi_pesme_sa_playliste", playlist_id=playlist_id, playlist_name=playlist_name))


@app.route('/dodaj_pesmu')
def dodaj_pesmu():
    playlist_id = request.args.get('playlist_id')
    song_uri = request.args.get('song_uri')
    playlist_name = request.args.get('playlist_name')
    sp = SpotifyMoja2(scope='playlist-read-private', app=app)

    # Nalazim vrednost imena liste na osnovu playlist_id
    playlists = sp.current_user_playlists()
    key_lista = [i for i in playlists if playlists[i] == playlist_id]
    playlist_name = key_lista[0]

    try:
        sp.playlist_add_items(playlist_id=playlist_id, items=[song_uri])
        print(f"Pesma uspešno dodata u listu {playlist_name}.")
    except spotipy.SpotifyException as e:
        print("Greška prilikom dodavanja pesme u  listu {}".format(e))

    return redirect(url_for("prikazi_pesme_sa_playliste", playlist_id=playlist_id, playlist_name=playlist_name))


@app.route('/premesti_pesmu')
def premesti_pesmu():
    playlist_id = request.args.get('playlist_id')
    range_start = request.args.get('range_start')
    playlist_name = request.args.get('playlist_name')

    sp = SpotifyMoja2(scope='playlist-read-private', app=app)
    sp.playlist_reorder_items(playlist_id, range_start=(int(range_start) - 1), insert_before=0, range_length=1,
                              snapshot_id=None)
    # sp.pormeni_poziciju_pesme(playlist_id=playlist_id, range_start=(int(range_start)))

    # sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope='playlist-read-private'))
    # SpotifyMoja.pormeni_poziciju_pesme(sp, playlist_id=playlist_id, range_start=(int(range_start)))
    return redirect(url_for('prikazi_pesme_sa_playliste', playlist_name=playlist_name, playlist_id=playlist_id))


# Za sad mi ne treba
# @app.route('/prikaz_pesama_playlista', methods=["GET", "POST"])
# def prikaz_pesama_playlista():
#     return render_template("prikaz_pesama_playlista")

@app.route('/forma_pretraga', methods=["GET", "POST"])
# @login_required
def forma_pretraga():
    forma = UnesiPodateZaPretraguForm()
    if forma.validate_on_submit():
        uneti_datum = forma.date.data
        return redirect(url_for("pronadji_pesme_i_napravi_listu", datum=uneti_datum))
    return render_template("forma_pretraga.html", form=forma)
    return render_template("forma_pretraga.html", form=forma, name=current_user.name,
                           logged_in=current_user.is_authenticated)


if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
