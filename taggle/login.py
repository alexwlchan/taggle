# -*- encoding: utf-8

import datetime as dt
import secrets

import attr
from flask import abort, redirect, render_template
from flask_login import login_required, login_user, logout_user, LoginManager
from flask_wtf import FlaskForm
from wtforms import PasswordField
from wtforms.validators import DataRequired


def configure_login(app, password):
    app.config['SECRET_KEY'] = secrets.token_bytes()

    login_manager = LoginManager()
    login_manager.init_app(app)

    @attr.s
    class User:
        password = attr.ib()

        is_active = True
        is_anonymous = False

        @property
        def is_authenticated(self):
            return self.password == password

        def get_id(self):
            return 1

    @login_manager.user_loader
    def load_user(user_id):
        return User(password=password)

    class LoginForm(FlaskForm):
        password = PasswordField('password', validators=[DataRequired()])

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        form = LoginForm()
        if form.validate_on_submit():
            user = User(form.data['password'])
            if not user.is_authenticated:
                return abort(401)

            login_user(user, remember=True, duration=dt.timedelta(days=365))
            return redirect('/')
        return render_template('login.html', form=form)

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect('/')

    @app.errorhandler(401)
    def page_forbidden(error):
        message = (
            "The server could not verify that you are authorized to access "
            "the URL requested. You either supplied the wrong credentials "
            "(e.g. a bad password), or your browser doesn't understand how to "
            "supply the credentials required."
        )
        return render_template(
            'error.html',
            title='401 Not Authorized',
            message=message), 401
