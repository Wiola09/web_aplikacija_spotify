import os
from flask import Flask, render_template, redirect, url_for, request, flash, current_app, jsonify, session
from flask_bootstrap import Bootstrap
from werkzeug.security import check_password_hash
from flask_login import LoginManager, login_user, current_user, login_required, logout_user
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# # Deo koji se odnosi na moje fajlove
from data_manager import db, DataManager, UserData, UserSema

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

def create_spotify_oauth(scope):
    return SpotifyOAuth(
        client_id=app.config['SPOTIPY_CLIENT_ID'],
        client_secret=app.config['SPOTIPY_CLIENT_SECRET'],
        redirect_uri=app.config['SPOTIPY_REDIRECT_URI'],
        scope=scope
    )

@app.route('/pocetak_spotify_auth_vracanje_linka')
def pocetak_spotify_auth_vracanje_linka():
    """
    Kada se radi autentifikacija, dobija se auth_url koja mora da se unese u python kod,
    ovde tor adim preko spotify_callback() funkcije
    :return:
    """
    scope = 'playlist-read-private'
    sp_oauth = create_spotify_oauth(scope)
    auth_url = sp_oauth.get_authorize_url()
    print(auth_url)
    return redirect(auth_url)

@app.route('/spotify_callback')
def spotify_callback():
    scope = 'playlist-read-private playlist-modify-private'
    sp_oauth = create_spotify_oauth(scope)
    session.pop('token_info', None)
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    session["token_info"] = token_info
    return redirect(url_for('spotify_podaci_posle_auth'))


@app.route('/spotify_podaci_posle_auth')
def spotify_podaci_posle_auth():
    token_info = session.get("token_info", None)
    if not token_info:
        print("cekaj cekaj bato petlja")
        return redirect('/pocetak_spotify_auth_vracanje_linka')

    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope='playlist-read-private'))

    # sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    #     scope='playlist-read-private',
    #     client_id=app.config['SPOTIPY_CLIENT_ID'],
    #     client_secret=app.config['SPOTIPY_CLIENT_SECRET'],
    #     redirect_uri=app.config['SPOTIPY_REDIRECT_URI'],
    #
    # ))
    playlists = sp.current_user_playlists()
    # print(playlists)
    return jsonify(playlists)


if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)