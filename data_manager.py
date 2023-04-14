"""
https://stackoverflow.com/questions/14789668/separate-sqlalchemy-models-by-file-in-flask
@johnny It means that SQLAlchemy() does not have to take app as parameter in the module it is used.
In most examples you can see SQLAlchemy(app) but it requires app from other scope in this case.
Instead you can use uninitialized SQLAlchemy() and use init_app(app) method later
as described in http://stackoverflow.com/a/9695045/2040487. –
"""
import os
# import pandas as pd
from flask_sqlalchemy import SQLAlchemy
# from flight_search import FlightSearch
import requests
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash



db = SQLAlchemy()

class DataManagerSema(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String(250), nullable=True)
    iata_code = db.Column(db.String(250), nullable=True)
    lowest_price = db.Column(db.Integer, nullable=True)
    email = db.Column(db.String(100), nullable=True)


class DataManager:
    # This class is responsible for talking to the Google Sheet.

    def vrati_sve_zapise_iz_db(self):
        lista_zapisa = db.session.query(DataManagerSema).all()
        return lista_zapisa

    def obrisi_zapis_iz_db(self, ime_grada_brisanje):
        ime_grada = DataManagerSema.query.filter_by(city=ime_grada_brisanje).first()
        print(ime_grada)
        try:
            ime_grada = DataManagerSema.query.filter_by(city=ime_grada_brisanje).first()
            db.session.delete(ime_grada)
            db.session.commit()
            print("obrisano")
        except:
            print("ajmo ponovo")

    def dodaj_grad_iata(self, iata, ime_grada):
        if DataManagerSema.query.filter_by(iata_code=iata).first():
            return "grad već psotoji"
        else:
            new_city = DataManagerSema(city=ime_grada, iata_code=iata)
            db.session.add(new_city)
            db.session.commit()

    def pretrazi_grad_db_po_vrednosti(self, polje_db, vrednost_za_pretragu):
        if polje_db == "city":
            return DataManagerSema.query.filter_by(city=vrednost_za_pretragu).first()
        elif polje_db == "iata_code":
            return DataManagerSema.query.filter_by(iata_code=vrednost_za_pretragu).first()
        elif polje_db == "email":
            return DataManagerSema.query.filter_by(email=vrednost_za_pretragu).first()
        else:
            pass


class UserSemaSpotify(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))


class UserData:
    def __init__(self, email, password, name):
        self.email = email
        self.password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
        self.name = name

    def add_user(self):
        new_user = UserSemaSpotify(email=self.email, password=self.password, name=self.name)
        db.session.add(new_user)
        db.session.commit()

    def pretrazi_db_po_korisniku(self, vrednost_za_pretragu):
        return UserSemaSpotify.query.filter_by(email=vrednost_za_pretragu).first()