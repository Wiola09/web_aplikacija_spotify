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

