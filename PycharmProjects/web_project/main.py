# -*- coding: utf-8 -*-
from flask import Flask, redirect, url_for, render_template, request, session, flash
from datetime import timedelta, datetime
from dateutil.tz import tzlocal
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = "hello"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///READY.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.permanent_session_lifetime = timedelta(days=5)

db = SQLAlchemy(app)

from admin.api import api
app.register_blueprint(api, url_prefix="/admin")


class Users(db.Model):
    id = db.Column("id", db.Integer, primary_key=True)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    username = db.Column(db.String(100))
    avatar = db.Column(db.String(100))
    hash_pass = db.Column(db.String(100))
    about_me = db.Column(db.String(140))
    last_seen = db.Column(db.DateTime, default=datetime.now())

    def __init__(self, first_name, last_name, email, username, avatar, hash_pass, about_me=""):
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.username = username
        self.avatar = avatar
        self.about_me = about_me
        self.hash_pass = hash_pass

    def to_dict(self):
        data = {
            'id': self.id,
            'last_seen': self.last_seen,
            'about_me': self.about_me,
            'email': self.email,
            'avatar': self.avatar
        }
        return data


class Posts(db.Model):
    _id = db.Column("id", db.Integer, primary_key=True)
    body = db.Column(db.Text)
    url = db.Column(db.String(100))
    time = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey(Users.id))
    user_username = db.Column(db.String(100))
    user_avatar = db.Column(db.String(100))

    def __init__(self, body, url, time, user_id, user_username, user_avatar):
        self.body = body
        self.url = url
        self.time = time
        self.user_id = user_id
        self.user_username = user_username
        self.user_avatar = user_avatar


class Follow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey(Users.id))
    following_id = db.Column(db.Integer, db.ForeignKey(Users.id))

    def __init__(self, follower_id, following_id):
        self.follower_id = follower_id
        self.following_id = following_id


class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30))
    hash_pass = db.Column(db.String(40))

    def __init__(self, username, hash_pass):
        self.username = username
        self.hash_pass = hash_pass


@app.route("/hello")
def hello():
    return render_template("main.html")


@app.route('/signup', methods=["GET", "POST"])
def sign_up():
    if "username" in session:
        return redirect(url_for("user", username=session["username"]))
    else:
        if request.method == "POST":
            session.permanent = True
            first_name = request.form["fname"]
            last_name = request.form["lname"]
            username = request.form["username"]
            email = request.form["email"]
            avatar = request.form["avatar"]
            password = generate_password_hash(request.form["password"])

            if Users.query.filter_by(username=username).all() or " " in username:
                flash("такой логин уже занят или содержит недопустимый знак")
                return render_template("signup.html")
            elif ".png" not in avatar and ".jpg" not in avatar and avatar != "":
                flash("формат вашего фото не поддерживаеся. Выберите фото с форматами PNG или JPG")
                return render_template("signup.html")
            else:
                session["first_name"] = first_name
                session["last_name"] = last_name
                session["email"] = email
                session["hash_password"] = password
                session["username"] = username
                session["avatar"] = avatar
                session["about_me"] = ""

                usr = Users(first_name, last_name, email, username, avatar, password)
                db.session.add(usr)
                db.session.commit()

                flash("вы успешно зарегистрировались", "info")
                return redirect(url_for("user", username=username))
        else:
            return render_template("signup.html")


@app.route("/login", methods=["POST", "GET"])
def login():
    if "username" in session:
        return redirect(url_for("user", username=session["username"]))
    else:
        if request.method == "POST":
            username = request.form["nick"]
            user = Users.query.filter_by(username=username).first()
            if user:
                password = request.form["password"]
                if check_password_hash(user.hash_pass, password):
                    session["first_name"] = user.first_name
                    session["last_name"] = user.last_name
                    session["email"] = user.email
                    session["hash_password"] = user.hash_pass
                    session["username"] = user.username
                    session["avatar"] = user.avatar
                    session["about_me"] = user.about_me
                    return redirect(url_for("user", username=username))
                else:
                    flash("Пароль, который вы ввели неправильный")
                    return render_template("login.html")
            else:
                flash("Логин, который вы ввели неправильный")
                return render_template("login.html")
        else:
            return render_template("login.html")


@app.route("/main", methods=["GET"])
def main():
    if "username" in session:
        posts = []
        user = Users.query.filter_by(username=session["username"]).first()
        for el in Follow.query.filter_by(follower_id=user.id).all():
            posts += Posts.query.filter_by(user_id=el.following_id).all()
        return render_template("main_page.html", posts=posts)
    else:
        return redirect(url_for("hello"))


@app.route("/user/<username>", methods=["POST", "GET"])
def user(username):
    if username == session["username"]:
        usr = Users.query.filter_by(username=username).first_or_404()
        usr.last_seen = datetime.utcnow()
        db.session.commit()

        posts = Posts.query.filter_by(user_id=usr.id).all()
        posts.reverse()
        return render_template('user.html', user=usr, posts=posts)
    else:
        my = Users.query.filter_by(username=session["username"]).first_or_404()  # me
        usr = Users.query.filter_by(username=username).first_or_404()  # friend
        posts = Posts.query.filter_by(user_id=usr.id).all()
        posts.reverse()
        follower = False
        following = False
        for his_followings in Follow.query.filter_by(follower_id=usr.id).all():
            if my.id == his_followings.following_id:
                follower = True
                break
            else:
                follower = False
        for him in Follow.query.filter_by(follower_id=my.id).all():
            if usr.id == him.following_id:
                following = True
                break
            else:
                following = False
        return render_template("friend.html", user=usr, posts=posts, follower=follower, following=following)


@app.route("/edit", methods=["POST", "GET"])
def edit_profile():
    if request.method == "POST":
        if "username" in session:
            username = session["username"]
            user = Users.query.filter_by(username=username).first_or_404()
            user.username = request.form["new_nick"]
            user.about_me = request.form["about_me"]
            session["username"] = user.username
            db.session.commit()
            return redirect(url_for("user", username=request.form["new_nick"]))
        else:
            return redirect(url_for("hello"))
    else:
        if "username" in session:
            username = session["username"]
            return render_template("edit.html", username=username)
        else:
            return redirect(url_for("hello"))


@app.route("/new_post/", methods=["GET", "POST"])
def new_post():
    if "username" in session:
        if request.method == "GET":
            return render_template("new_post.html")
        else:
            User = Users.query.filter_by(username=session["username"]).first()
            user_id = User.id
            user_username = User.username
            user_avatar = User.avatar
            body = request.form["body"]
            url = request.form["url"]
            time = datetime.now(tzlocal())
            post = Posts(body, url, time, user_id, user_username=user_username, user_avatar=user_avatar)
            db.session.add(post)
            db.session.commit()
            return redirect(url_for("user", username=User.username))
    else:
        return redirect(url_for("hello"))


@app.route("/search", methods=["POST", "GET"])
def search():
    if "username" in session:
        if request.method == "GET":
            return render_template("search.html")
        else:
            username = request.form["userName"]
            first_name = request.form["firstName"]
            last_name = request.form["lastName"]
            if first_name == last_name == "":
                column = "username"
                keyword = username
            elif username == last_name == "":
                column = "first_name"
                keyword = first_name
                # User = Users.query.filter(Users.first_name.like(f'%{first_name[1:]}%')).all()
            elif username == first_name == "":
                column = "last_name"
                keyword = last_name
                # User = Users.query.filter(Users.last_name.like(f'%{last_name[1:]}%')).all()
            else:
                return redirect(url_for("search"))
            return redirect(url_for("results", column=column, keyword=keyword))
    else:
        return redirect(url_for("hello"))


@app.route("/search/result/<column>/<keyword>", methods=["POST", "GET"])
def results(column, keyword):
    if request.method == "GET":
        if column == "username":
            users = Users.query.filter_by(username=keyword).all()
        elif column == "first_name":
            users = Users.query.filter(Users.first_name.like(f'%{keyword[1:]}%')).all()
        else:
            users = Users.query.filter(Users.last_name.like(f'%{keyword[1:]}%')).all()
        return render_template("result.html", users=users)
    else:
        username = request.form["userName"]
        first_name = request.form["firstName"]
        last_name = request.form["lastName"]
        if first_name == last_name == "":
            column = "username"
            keyword = username
        elif username == last_name == "":
            column = "first_name"
            keyword = first_name
            # User = Users.query.filter(Users.first_name.like(f'%{first_name[1:]}%')).all()
        elif username == first_name == "":
            column = "last_name"
            keyword = last_name
            # User = Users.query.filter(Users.last_name.like(f'%{last_name[1:]}%')).all()
        else:
            return redirect(url_for("search"))
        return redirect(url_for("results", column=column, keyword=keyword))


@app.route("/add/<friend>", methods=["GET", "POST"])
def add(friend):
    if "username" in session:
        follower_id = Users.query.filter_by(username=session["username"]).first().id
        following_id = Users.query.filter_by(username=friend).first().id
        follow = Follow(follower_id, following_id)
        db.session.add(follow)
        db.session.commit()
        return redirect(url_for("user", username=friend))
    else:
        return redirect(url_for("hello"))


@app.route("/logout")
def logout():
    session.pop("username", None)
    session.pop("email", None)
    session.pop("first_name", None)
    session.pop("last_name", None)
    session.pop("hash_password", None)
    session.pop("avatar", None)
    session.pop("about_me", None)
    return redirect(url_for("hello"))


@app.route("/messages")
def messages():
    return render_template("messages.html")


if __name__ == "__main__":
    db.create_all()
    app.run()
