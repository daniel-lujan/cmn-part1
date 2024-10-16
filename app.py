import sqlite3
from uuid import uuid4

from flask import Flask, Response, g, render_template, request
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    get_jwt_identity,
    jwt_required,
)

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = "super-secret"

jwt = JWTManager(app)

DATABASE_FILE = "database.db"
db = sqlite3.connect(DATABASE_FILE)


def init_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE_FILE)
    db.execute(
        """CREATE TABLE IF NOT EXISTS users (
        username varchar NOT NULL,
        "password" varchar NOT NULL,
        CONSTRAINT users_pk PRIMARY KEY (username))"""
    )

    try:
        db.execute("INSERT INTO users (username, password) VALUES ('daniel', 'root')")
        db.execute(
            "INSERT INTO users (username, password) VALUES ('juan pablo', 'root')"
        )
    except:
        pass

    db.execute(
        """CREATE TABLE IF NOT EXISTS comments (
        id VARCHAR NOT NULL,
        comment varchar NOT NULL,
        user varchar NOT NULL REFERENCES users(username),
        CONSTRAINT comments_pk PRIMARY KEY (id))"""
    )
    db.commit()


def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE_FILE)
        init_db()
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


@app.route("/")
def index():

    cursor = get_db().cursor()

    cursor.execute("SELECT * FROM comments")
    comments = cursor.fetchall()

    cursor.close()

    return render_template("index.html", comments=comments)


@app.route("/register", methods=["POST"])
def register():
    username = request.json["username"]
    password = request.json["password"]

    cursor = get_db().cursor()

    try:
        cursor.execute(
            f"INSERT INTO users (username, password) VALUES ('{username}', '{password}')"
        )
        cursor.close()

        get_db().commit()
    except:
        cursor.close()
        return Response(status=400)

    return Response(status=201)


@app.route("/login", methods=["POST"])
def login():
    username = request.json["username"]
    password = request.json["password"]

    cursor = get_db().cursor()

    try:
        cursor.execute(
            f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
        )
        res = cursor.fetchone()
    except:
        res = None
    finally:
        cursor.close()

    if res is None:
        return Response(status=401)

    return {
        "access_token": create_access_token(identity=username),
        "username": username,
    }


@app.route("/comments")
def get_comments():
    cursor = get_db().cursor()

    cursor.execute("SELECT * FROM comments")
    comments = cursor.fetchall()

    cursor.close()

    return list({"user": c[2], "comment": c[1]} for c in comments)


@app.route("/comments", methods=["POST"])
@jwt_required()
def post_comment():
    username = get_jwt_identity()
    comment = request.json["comment"]

    try:
        db = get_db()
        cursor = db.cursor()
        id_ = str(uuid4())
        cursor.execute(
            f"INSERT INTO comments (id, comment, user) VALUES ('{id_}', '{comment}', '{username}')"
        )
        cursor.close()
        db.commit()
    except:
        return Response(status=400)
    finally:
        cursor.close()

    return {
        "id": id_,
        "user": username,
        "comment": comment,
    }


@app.route("/reset-db")
def reset_db():
    token = request.args.get("token")
    if token != "EFKO":
        return Response(status=401)
    init_db()
    return Response(status=200)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
