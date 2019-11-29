import os

from helpers import apology, login_required
from flask import Flask, session, redirect, render_template, request, jsonify
import json
import requests
from flask_session import Session
from markupsafe import Markup

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
# Import table definitions.
#from models import *

app = Flask(__name__)
# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URL']
# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
@login_required
def index():
    return render_template("index.html")


@app.route("/book", methods=["GET", "POST"])
@login_required
def book():
    isbn = request.args.get("isbn")
    res1 = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "hYq7LZ3pS3xoQTShFaX9A", "isbns": isbn})
    if res1.status_code != 200:
      raise Exception("ERROR: API request unsuccessful.")
    result1 = res1.json()

    res2 = requests.get("https://www.goodreads.com/book/show.json", params={"key": "hYq7LZ3pS3xoQTShFaX9A", "id": result1["books"][0]["id"]})
    if res2.status_code != 200:
      raise Exception("ERROR: API request unsuccessful.")
    result2 = res2.json()

    res3 = requests.get("https://www.goodreads.com/book/show.xml", params={"key": "hYq7LZ3pS3xoQTShFaX9A", "id": result1["books"][0]["id"]})
    if res3.status_code != 200:
      raise Exception("ERROR: API request unsuccessful.")
    root = ET.fromstring(res3.content)
    book_details = []
    for book in root.findall('book'):
        book_details.append(book.find('title').text)
        book_details.append(book.find('publication_year').text)
        book_details.append(book.find('publisher').text)
        book_details.append(book.find('description').text)
        book_details.append(BeautifulSoup(book.find('small_image_url').text))

    print(book_details)
    return render_template("book.html", isbn=isbn, result1=result1, result2=result2, book_details=book_details)


@app.route("/search", methods=["GET", "POST"])
def search():
    user_input=request.args.get("q")
    input_type=str(request.args.get("t"))  # javascript returns search type(isbn, title,author,or year)

    if(user_input is None or input_type is None):
        return apology("Must specify search type and search string", 500)

    results=[];
    # Query differently based on the search type: isbn/title/author/year.
    if(input_type=="byIsbn"):
        print("query by isbn")
        results = db.execute("SELECT * FROM books WHERE isbn LIKE '%'||:user_input||'%'",{"user_input":str(user_input)}).fetchall()
    elif(input_type=="byTitle"):
        print("query by title")
        results = db.execute("SELECT * FROM books WHERE title LIKE '%'||:user_input||'%'",{"user_input":str(user_input)}).fetchall()
    elif(input_type=="byAuthor"):
        print("query by author")
        results = db.execute("SELECT * FROM books WHERE author LIKE '%'||:user_input||'%'",{"user_input":str(user_input)}).fetchall()
    elif(input_type=="byYear"):
        print("query by year")
        results = db.execute("SELECT * FROM books WHERE year::TEXT LIKE '%'||:user_input||'%'",{"user_input":int(user_input)}).fetchall()

    res = [(result.isbn, result.title, result.author, result.year) for result in results]
    return jsonify(res)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    # Forget any user_id
    session.clear()
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        cursor = db.execute("SELECT * FROM users WHERE username = :username",{"username":request.form.get("username")})
        rows = cursor.fetchone()
        # Ensure username exists and password is correct
        if int(cursor.rowcount)!=1 or not check_password_hash(rows.hash, request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows.id
        session["user_username"] = rows.username

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""
    # Forget any user_id
    session.clear()
    # Redirect user to login form
    return redirect("/")


@app.route("/check", methods=["GET"])   #Get user input everytime OnKeyUp
def check():
    """Return true if username available, else false, in JSON format"""
    username_input = request.args.get("username")
    #print(username_input)
    # Query database for existing usernames
    username_database = db.execute("SELECT username FROM users").fetchall()
    username_database_list = [name.username for name in username_database]

    # length at least 1 and does not already belong to a user in the database
    if(len(username_input) > 1 and (username_input not in username_database_list)):
        return jsonify(True)
    else:
        return jsonify(False)

#Keep going from here
@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # users reaching register via POST method
    if request.method == "POST":
        # Handling username
        username = request.form.get("username")
        cursor = db.execute("SELECT * FROM users WHERE username = :username",
                          {"username":username})
        rows = cursor.fetchall()

        if(not username):
            return apology("input is blank", 400)
        elif(cursor.rowcount != 0):
            return apology("username already exists", 400)

        # Handling password
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        if(not password):
            return apology("password is blank")
        elif(password != confirmation):
            return apology("passwords do not match")

        db.execute("INSERT INTO users (username, hash) VALUES (:username, :password_hash)",
                    {"username":request.form.get("username"),
                    "password_hash":generate_password_hash(password)})
        db.commit()
        return redirect("/")

    # users reaching register via GET method
    else:
        return render_template("register.html")


@app.route("/changePassword", methods=["GET", "POST"])
@login_required
def changePassword():
    """Change password."""

    # User reached route via GET (as by clicking a link or via redirect)
    if request.method == "GET":
        return render_template("changePassword.html")

     # User reached route via POST (as by submitting a form via POST)
    else:
        # Ensure password was submitted
        if not request.form.get("password"):
            return apology("must provide password", 403)

        # Query all information about the user
        cursor = db.execute("SELECT * FROM users WHERE id = :user_id",
                          {"user_id":session["user_id"]})
        rows = cursor.fetchone()

        # Ensure username exists and password is correct
        if not check_password_hash(rows.hash, request.form.get("password")):
            return apology("invalid password", 403)  # if does not match, render an apology
        else:
            newPassword = request.form.get("newPassword")
            confPassword = request.form.get("confPassword")
            if(not newPassword):
                return apology("New password is blank")
            elif(newPassword != confPassword):
                return apology("New passwords do not match")
            else:
                # When all are correct
                db.execute("UPDATE users SET hash = :confPassword_hash WHERE id = :user_id", {"confPassword_hash":generate_password_hash(confPassword),
                           "user_id":session["user_id"]})
                db.commit()

        # after altering, require user to login again
        return render_template("login.html")

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)
