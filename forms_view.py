from flask_wtf import FlaskForm
from datetime import date, timedelta
from wtforms import StringField, SubmitField, PasswordField, DateField, SelectField, \
    SelectMultipleField, HiddenField, EmailField, IntegerField
from wtforms.validators import DataRequired, NumberRange, InputRequired, ValidationError
# from flask_ckeditor import CKEditorField


THEN_YEARS_AGO = date.today() - 10 * timedelta(days=365)

"%d""/""%m""/""%Y"
# #WTForm


class UnesiPodateZaPretraguForm(FlaskForm):
    date = DateField('Datum liste top pesama', format='%Y-%m-%d', default=THEN_YEARS_AGO, validators=[DataRequired()])
    submit_flight_data = SubmitField("Pretraži pesme")


class DodajPesmu(FlaskForm):
    #You can narrow down your search using field filters.
    # The available filters are album, artist, track, year, upc, # tag:hipster, tag:new, isrc, and genre.
    # Each field filter only applies to certain result types.
    # https://developer.spotify.com/documentation/web-api/reference/search
    track = StringField("Naziv", validators=[DataRequired()], render_kw={"placeholder": "Enter Song Name"})
    artist = StringField("Umetnik", render_kw={"placeholder": "Enter Song Artist"})
    year = StringField("Godina", render_kw={"placeholder": "Enter Song Year"})
    submit_flight_data = SubmitField("Pretraži pesmu")

