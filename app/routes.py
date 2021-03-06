from flask import render_template, flash, redirect, url_for, request
from flask import abort
from app import app
from app.forms import LoginForm, RegistrationForm, EditProfileForm
from app.forms import PostForm, ResetPasswordRequestForm, ResetPasswordForm
from app.email import send_password_reset_email
from flask_login import current_user, login_user
from flask_login import logout_user, login_required
from app.models import Users, get_user, Posts, get_posts
from werkzeug.urls import url_parse
from datetime import datetime


@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        current_user.update()


@app.route("/", methods=["GET","POST"])
@app.route("/index", methods=["GET","POST"])
@login_required
def index ():
    form=PostForm()
    if form.validate_on_submit():
        post=Posts(body=form.body.data, timestamp=datetime.utcnow(),
                link=form.link.data, user_id=current_user.id)
        post.write(current_user)
        flash("Your post is now live!")
        return redirect(url_for("index"))
    page=request.args.get("page", 1, type=int)
    all_posts = current_user.followed_posts()
    posts_per_page=app.config["POSTS_PER_PAGE"]
    #The following statement helps implement pagination.
    posts = all_posts[(page-1)*posts_per_page:page*posts_per_page]
    next_url = url_for("index", page=page+1)\
            if (len(all_posts) > page*posts_per_page) else None
    prev_url = url_for("index", page=page-1)\
            if (page-1 > 0) else None
    return render_template("index.html",
            title = "Home", form=form, 
            posts=posts, next_url=next_url,
            prev_url=prev_url)


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
        next_page=request.args.get("next")
        if not next_page or url_parse(next_page).netloc != "":
            next_page = url_for("index")
        return redirect(url_for("index"))
    return render_template("login.html", title = "Sign In", form = form)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/register", methods=["GET","POST"])
def register():
    if current_user.is_authenticated:
        return redirect (url_for("index"))
    form = RegistrationForm()
    if form.validate_on_submit():
        user=Users(username=form.username.data, rollno=form.rollno.data,
                   email=form.email.data)
        user.set_password(form.password.data)
        user.write()
        #I need to define a method for class Users to write 
        #objects to database
        #user.write()
        flash("Congratulations, you are now a registered user!")
        return redirect(url_for("login"))
    return render_template("register.html", title="Register", form=form)


@app.route("/edit_profile", methods=["GET","POST"])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        current_user.update()
        flash("Your changes have been saved.")
        return redirect(url_for("edit_profile"))
    elif request.method == "GET":
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template("edit_profile.html", title = "Edit Profile",
            form=form)


@app.route("/user/<username>")
@login_required
def user(username):
    user=get_user(username=username)
    if not user:
        """If no Users object is found with the given username then the
        abort function forces a 404 error."""
        abort(404)
    posts=[{"author": user, "body": "Test post #1"},
            {"author": user, "body": "Test post #2"}
            ]
    return render_template("user.html", user=user, posts=posts)

@app.route("/follow/<username>")
@login_required
def follow(username):
    user=get_user(username=username)
    if user is None:
        flash("User {} not found.".format(username))
        return redirect(url_for("index"))
    if user==current_user:
        flash("You cannot follow yourself!")
        return redirect(url_for("user",username=username))
    current_user.follow(user)
    flash("You are following {}!".format(username))
    return redirect(url_for("user",username=username))


@app.route("/unfollow/<username>")
@login_required
def unfollow(username):
    user=get_user(username=username)
    if user is None:
        flash("User {} not found.".format(username))
        return redirect(url_for("index"))
    if user==current_user:
        flash("You cannot unfollow yourself!")
        return redirect(url_for("user",username=username))
    current_user.unfollow(user)
    flash("You are not following {}.".format(username))
    return redirect(url_for("user",username=username))

@app.route("/explore")
@login_required
def explore():
    page = request.args.get("page", 1, type=int)
    posts_per_page = app.config["POSTS_PER_PAGE"]
    all_posts=get_posts()
    posts=all_posts[(page-1)*posts_per_page:page*posts_per_page]
    next_url = url_for("explore", page=page+1)\
            if (len(all_posts) > page*posts_per_page) else None
    prev_url = url_for("explore", page=page-1)\
            if (page-1 > 0) else None
    return render_template("index.html", title="Explore", posts=posts,
            next_url=next_url, prev_url=prev_url)

@app.route("/reset_password_request", methods = ["GET", "POST"])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = get_user(email=form.email.data)
        if user:
            send_password_reset_email(user)
        flash("Check your email for the instructions to reset your password")
        return redirect(url_for("login"))
    return render_template("reset_password_request.html",
                           title="Reset Password", form=form)


@app.route("/reset_password/<token>", methods=["GET","POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect (url_for("index"))
    user = Users.verify_reset_password_token(token)
    if not user:
        return redirect(url_for("index"))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        user.update()
        flash("Your password has been reset.")
        return redirect(url_for("login"))
    return render_template("reset_password.html", form=form)
