import os
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
from spotify_baratanje import SpotifyMoja
from spotify_utils import SpotifyMoja2

APP_SECRET_KEY = os.getenv("APP_SECRET_KEY", "default_value")

app = Flask(__name__)
app.config['SECRET_KEY'] = APP_SECRET_KEY
Bootstrap(app)

# Deo vezan za spotify
SPOTIPY_CLIENT_ID = os.environ["SPOTIPY_CLIENT_ID"]
SPOTIPY_CLIENT_SECRET = os.environ["SPOTIPY_CLIENT_SECRET"]
SPOTIPY_REDIRECT_URI = os.environ["SPOTIPY_REDIRECT_URI"]
app.config["SPOTIPY_CLIENT_ID"] = SPOTIPY_CLIENT_ID
app.config["SPOTIPY_CLIENT_SECRET"] = SPOTIPY_CLIENT_SECRET
app.config["SPOTIPY_REDIRECT_URI"] = SPOTIPY_REDIRECT_URI

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


@app.route('/')
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
            return redirect(url_for('pocetna_aplikacija', name=current_user.name))

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


@app.route('/pocetak_spotify_auth_vracanje_linka')
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
    print(auth_url)
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
    odabrana_lista = '2003-08-12 Billboard 100'

    rezultat = sp.playlist_items(liste_recnik[odabrana_lista])

    # return jsonify(rezultat['items'][0])  # Kod vraca JSON podatke i samo ejdnoj pesmi
    return render_template("prikaz_pesama_playlista.html", pesme=rezultat['items'], lista=odabrana_lista)


@app.route('/pronadji_pesme_i_napravi_listu')
def pronadji_pesme_i_napravi_listu():
    """
    Pronalazi pemse iz liste, i kreira sa njima novu PL,
     TODO: Napraviti pravu listu pesama i dodati je kao argument u funkciju pronadji_pesme_iz_liste
    :return:
    """
    token_info = session.get("token_info", None)
    if not token_info:
        print("Nema token_info")
        return redirect('/pocetak_spotify_auth_vracanje_linka')

    sp = SpotifyMoja2(scope='playlist-read-private', app=app)
    song_uris = sp.pronadji_pesme_iz_liste()
    sp.create_playlist_and_add_songs(song_uris)

    return "pogledaj liste"


@app.route('/obrisi_pesmu')
def obrisi_pesmu():

    playlist_id = request.args.get('playlist_id')
    song_id = request.args.get('song_id')
    sp = SpotifyMoja2(scope='playlist-read-private', app=app)

    try:
        sp.playlist_remove_all_occurrences_of_items(playlist_id=playlist_id, items=[song_id])
        print("Pesma uspešno obrisana iz liste.")
    except spotipy.SpotifyException as e:
        print("Greška prilikom brisanja pesme iz liste: {}".format(e))

    return redirect(url_for("spotify_podaci_posle_auth"))


@app.route('/premesti_pesmu')
def premesti_pesmu():
    playlist_id = request.args.get('playlist_id')
    range_start = request.args.get('range_start')

    sp = SpotifyMoja2(scope='playlist-read-private', app=app)
    sp.playlist_reorder_items(playlist_id, range_start=(int(range_start) - 1), insert_before=5, range_length=1,
                              snapshot_id=None)
    # sp.pormeni_poziciju_pesme(playlist_id=playlist_id, range_start=(int(range_start)))

    # sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope='playlist-read-private'))
    # SpotifyMoja.pormeni_poziciju_pesme(sp, playlist_id=playlist_id, range_start=(int(range_start)))

    return redirect(url_for("spotify_podaci_posle_auth"))


@app.route('/prikaz_pesama_playlista', methods=["GET", "POST"])
def prikaz_pesama_playlista():
    return render_template("prikaz_pesama_playlista")


if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
