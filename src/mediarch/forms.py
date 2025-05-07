from flask_wtf import FlaskForm
from wtforms import PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError

from .models import AccountType, User


class RegistrationForm(FlaskForm):
    """Form for user registration."""
    username = StringField(
        "Username",
        validators=[
            DataRequired(),
            Length(min=4, max=25, message="Username must be between 4 and 25 characters."),
        ],
    )
    email = StringField("Email", validators=[DataRequired(), Email(message="Invalid email address.")])
    account_type = SelectField(
        "Account Type",
        choices=[(role.value, role.name.title()) for role in AccountType],
        validators=[DataRequired()],
        default=AccountType.PATIENT.value
    )
    # Fields specific to Patient account type
    first_name = StringField("First Name", validators=[DataRequired(), Length(min=1, max=50)])
    last_name = StringField("Last Name", validators=[DataRequired(), Length(min=1, max=50)])

    password = PasswordField(
        "Password",
        validators=[DataRequired(), Length(min=8, message="Password must be at least 8 characters long.")],
    )
    confirm_password = PasswordField(
        "Confirm Password", validators=[DataRequired(), EqualTo("password", message="Passwords must match.")]
    )
    submit = SubmitField("Register")

    def validate_username(self, username: StringField) -> None:  # noqa: PLR6301
        """Validate that the username is not already taken."""
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError("That username is already taken. Please choose a different one.")

    def validate_email(self, email: StringField) -> None:  # noqa: PLR6301
        """Validate that the email is not already taken."""
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError("That email address is already registered. Please choose a different one.")


class LoginForm(FlaskForm):
    """Form for user login."""
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")
