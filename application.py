import os

from flask import g, Flask, jsonify, flash, session, redirect, render_template, request, session
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


@app.route("/")
@login_required
def index():
    """Main page"""
    return render_template("index.html", request ="")


@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    if request.method == "POST":
        if request.form.get("search_str") != '':
            req = request.form.get("search_str")
            books = db.execute("SELECT id, isbn, title, author, year FROM books WHERE isbn like :search_str OR title like :search_str OR author like :search_str ORDER BY title, author, year", 
                          {"search_str": req+'%'}).fetchall()
            cnt = db.execute("SELECT count(*) as cnt FROM books WHERE isbn like :search_str OR title like :search_str OR author like :search_str", 
                          {"search_str": request.form.get("search_str")+'%'}).fetchone()
            return render_template("index.html", books = books, cnt = cnt.cnt, req = req)
        else:
            return render_template("index.html", noresult = "No results.")
    if request.method == "GET":
        return redirect("/")

@app.route("/my_reviews", methods=["GET"])
@login_required
def my_reviews():
    reviews = db.execute("SELECT rew.rating as rating, rew.review as review, boo.id as book_id, boo.title as title, boo.author as author FROM books as boo, reviews as rew WHERE user_id = :user_id AND rew.book_id = boo.id", {"user_id": session["user_id"]}).fetchall()
    return render_template("my_reviews.html", reviews=reviews)


@app.route("/change_review", methods=["POST"])
@login_required
def change_review():
    book_id = request.form.get('book_id')
    review_text = request.form.get('review_text')
    if book_id:
        if db.execute("SELECT * FROM reviews WHERE book_id = :book_id AND user_id = :user_id", {"book_id": book_id, "user_id": session["user_id"]}).rowcount != 0:
            if db.execute("UPDATE reviews SET review = :review_text WHERE book_id = :book_id AND user_id = :user_id",{"review_text" : review_text, "book_id": book_id, "user_id": session["user_id"]}):
                db.commit()
                review = db.execute("SELECT * FROM reviews WHERE book_id = :book_id AND user_id = :user_id", {"book_id": book_id, "user_id": session["user_id"]}).fetchone()
                return render_template("review.html",  review=review, book_id=book_id)
            else:
                return render_template("review.html",  message="Problem with UPDATE")
        
        else: 
            new_id = db.execute("INSERT INTO reviews (book_id, user_id, review) VALUES (:book_id, :user_id, :review_text) RETURNING id",
                {"book_id":book_id,
                 "user_id":session["user_id"],
                 "review_text":review_text})
            db.commit()
            if new_id != 0:
                review = db.execute("SELECT * FROM reviews WHERE book_id = :book_id AND user_id = :user_id", {"book_id": book_id, "user_id": session["user_id"]}).fetchone()
                return render_template("review.html",  review=review, book_id=book_id)
            else:
                return render_template("review.html",  message="Problem with INSERT")
    else:
        return render_template("review.html",  message="Wrong parameters 'book_id' or 'rating'") 


@app.route("/change_rating", methods=["POST"])
@login_required
def change_rating():
    book_id = request.form.get('book_id')
    rating = request.form.get('rating')
    if book_id and rating and int(rating) >=0 and int(rating) <6:
        if db.execute("SELECT * FROM reviews WHERE book_id = :book_id AND user_id = :user_id", {"book_id": book_id, "user_id": session["user_id"]}).rowcount != 0:
            if db.execute("UPDATE reviews SET rating = :rating WHERE book_id = :book_id AND user_id = :user_id",{"rating" : rating, "book_id": book_id, "user_id": session["user_id"]}):
                db.commit()
                review = db.execute("SELECT * FROM reviews WHERE book_id = :book_id AND user_id = :user_id", {"book_id": book_id, "user_id": session["user_id"]}).fetchone()
                return render_template("rating.html",  review=review, book_id=book_id)
            else:
                return render_template("rating.html",  message="Problem with UPDATE")
        
        else: 
            new_id = db.execute("INSERT INTO reviews (book_id, user_id, rating) VALUES (:book_id, :user_id, :rating) RETURNING id",
                {"book_id":book_id,
                 "user_id":session["user_id"],
                 "rating":rating})
            db.commit()
            if new_id != 0:
                review = db.execute("SELECT * FROM reviews WHERE book_id = :book_id AND user_id = :user_id", {"book_id": book_id, "user_id": session["user_id"]}).fetchone()
                return render_template("rating.html",  review=review, book_id=book_id)
            else:
                return render_template("rating.html",  message="Problem with INSERT")
    else:
        return render_template("rating.html",  message="Wrong parameters 'book_id' or 'rating'") 

@app.route("/books/<int:book_id>")
@login_required
def books(book_id):
    """Lists details about a book."""
    book = db.execute("SELECT * FROM books WHERE id = :id", {"id": book_id}).fetchone()
    review = db.execute("SELECT * FROM reviews WHERE book_id = :book_id AND user_id = :user_id", {"book_id": book_id, "user_id": session["user_id"]}).fetchone()
    """тут делаем вложенный запрос IN чтобы удалить строки пользователей, которые удалили и рейтинг и отзыв """
    others_reviews = db.execute("SELECT r.rating, r.review, u.username, CASE WHEN length(review) > 20 THEN substr(review, 1, 20) || ' ...' ELSE review END short_review FROM reviews as r, users as u WHERE r.user_id IN(select r.user_id where r.review != '' or r.rating > 0 ) AND r.book_id = :book_id AND r.user_id != :user_id AND r.user_id = u.id", {"book_id": book_id, "user_id": session["user_id"]}).fetchall()
    if book is None:
        return render_template("index.html", noresult = "There is no a book")
    import requests
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "eFmttVNjVbGJJYPv11W0jA", "isbns": book.isbn})
    return render_template("book.html", book=book, reviews=res.json(), review=review, others_reviews=others_reviews)


@app.route("/api/<string:isbn>")
@login_required
def books_api(isbn):
    print(f"{isbn}")
    if db.execute("SELECT id from books where isbn = :isbn",{"isbn": isbn}).rowcount == 0:
        return jsonify({"error":"invalid ISBN"}), 404
    else:
        book_info  = db.execute("SELECT * from books WHERE isbn = :isbn",{"isbn": isbn}).fetchone()
        rating = db.execute("SELECT COUNT (CASE WHEN reviews.rating >0 THEN reviews.rating ELSE NULL END) as rc, CAST(SUM (reviews.rating) AS DEC(3,2)) / COUNT (CASE WHEN reviews.rating >0 THEN reviews.rating ELSE NULL END) as average from reviews WHERE book_id = :book_id", {"book_id" : book_info.id}).fetchone()
        if not rating.average:
            average = 0
        else:
            average = rating.average
        return jsonify({"title":book_info.title,
                "author":book_info.author,
                "year":book_info.year,
                "isbn":book_info.isbn,
                "review_count":rating.rc,
                "average_score":average}), 200


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            flash('You must provide username')
            return redirect("/login")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash('You must provide password')
            return redirect("/login")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :u_name",
                          {"u_name": request.form.get("username")}).fetchall()

        # Ensure username exists and password is correct
        if db.execute("SELECT * FROM users WHERE username = :u_name", 
                          {"u_name": request.form.get("username")}).rowcount == 0 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            flash('Invalid username and/or password')
            return redirect("/login")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        flash('You were successfully logged in')
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()
    # Redirect user to login form
    return redirect("/login")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
            # Ensure username was submitted
        if not request.form.get("username"):
            flash('You must provide username')
            return redirect("/register")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash('You must provide password')
            return redirect("/register")

         # Ensure password was submitted
        elif request.form.get("password") != request.form.get("confirmation"):
            flash('Password confirmation is not valid')
            return redirect("/register")

        elif db.execute("SELECT username FROM users WHERE username = :check_name",
                        {"check_name": request.form.get("username")}).rowcount == 1: 
            flash('Username ' + request.form.get("username") + ' already exists')
            return redirect("/register")

        user_name = request.form.get("username")
        hashh = generate_password_hash(request.form.get("password"), "sha256")
        new_id = db.execute("INSERT INTO users (username, hash) VALUES (:u_name, :hashh) RETURNING id", {"u_name": user_name, "hashh": hashh}).fetchone()
        db.commit()

        if not new_id:
            flash('Database error')
            return redirect("/register")
        else:
            session.clear()
            session["user_id"] = new_id[0] # если без индекса, то возвращало странный формат типа (4,)
            flash('You were successfully registred')
            return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("/register.html")
        
@app.route("/check", methods=["GET"])
def check():
    name_test = db.execute("SELECT username FROM users WHERE username = :test_name",
                           {"test_name":request.args.get('username')}).fetchone()

    if name_test:
        return jsonify(False)
    else:
        return jsonify(True)
