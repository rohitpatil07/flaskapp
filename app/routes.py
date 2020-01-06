from flask import render_template, flash, redirect, url_for
from app import app
from app.forms import LoginForm
from flask_login import current_user, login_user
from flask_login import logout_user, login_required
from app.models import Users, get_user


@app.route("/")
@app.route("/index")
@login_required
def index ():
    user = {"username":"Mukul"}
    posts = [{"author" : {"username" : "Sunita"},
            "body" : "Beautiful day in Kharghar"} ,
            { "author" : {"username" : "Vishav"} ,
                "body" : "That child was way too cute."}
            ]
    return render_template("index.html",
            title = "Home", 
            user = user,
            posts=posts)


@app.route("/login", methods = ["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = LoginForm()
    if form.validate_on_submit():
        user=get_user(username=form.username.data)
        if user is None or not user.check_password(form.password.data):
            flash("Invalid Username or Password")
            return redirect(url_for("login"))
        login_user(user, remember=form.remember_me.data)
        return redirect(url_for("index"))
    return render_template("login.html", title = "Sign In", form = form)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("index"))

