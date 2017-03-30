from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import gettempdir

from helpers import *

# configure application
app = Flask(__name__)

# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# custom filter
app.jinja_env.filters["usd"] = usd

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = gettempdir()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///league.db")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock."""
    rows = db.execute("SELECT cash FROM users WHERE id = :id", id=session['user_id'])
    cash = rows[0]["cash"]
    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # ensure stock entered
        if not request.form.get("stock"):
            return apology("must provide stock symbol")
            
        # checks if share amount is not empty
        if not request.form.get("shares"):
            return apology("share field empty")
        
        # checks if shares is greater than one
        shares = request.form.get("shares")
        try:
            shares = int(shares)
        except ValueError:
            return apology("Invalid shares entry")
        if shares < 1:
            return apology("invalid shares amount")

        # gets quote and checks if valid
        quote = lookup(request.form.get("stock"))
        if quote == None:
            return apology("Invalid Stock Symbol")
        
        #calculates cost of shares
        cost = quote['price']
        if cash < cost:
            return apology("Insufficient Funds")
        
        #add stock to portfolio
        db.execute("INSERT INTO history (username, stock, shares, cost, symbol) VALUES (:username, :stock, :shares, :cost, :symbol)", username=session["username"], stock=quote['name'], shares=shares, cost=cost, symbol=request.form.get("stock").upper())
        
        #subtract cash from user
        db.execute("UPDATE users SET cash = :cash - :cost WHERE id = :id", cash=cash, cost=cost*shares, id=session["user_id"])
        
        return redirect(url_for("index"))
    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        cash = usd(cash)
        return render_template("buy.html", cash=cash)

@app.route("/history", methods=["GET"])
@login_required
def history():
    """Show history of transactions."""
    rows = db.execute("SELECT cash FROM users WHERE id = :id", id=session["user_id"])
    cash = rows[0]["cash"]
    stocks = db.execute("SELECT * FROM history where username = :username", username=session["username"])
    return render_template("history.html", stocks=stocks)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
            return apology("invalid username and/or password")

        # remember which user has logged in
        session["user_id"] = rows[0]["id"]
        session["username"] = rows[0]["username"]

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))

@app.route("/search", methods=["GET", "POST"])
def quote():
    """Queries Stock Quotes"""
    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure stock entered
        if not request.form.get("stock"):
            return apology("must provide stock symbol")

        # gets quote and checks if valid
        quote = lookup(request.form.get("stock"))
        if quote == None:
            return apology("Invalid Stock Symbol")
        
        #return quote
        return render_template("searched.html", name=quote['name'], price=usd(quote['price']), symbol=quote['symbol'])
    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("search.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Registers a user."""
    
    # forget any user_id
    session.clear()
    
    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")
            
        # ensure confirmation password was submitted
        elif not request.form.get("password2"):
            return apology("must provide confirmation password")
        
        # ensures passwords match    
        elif request.form.get("password") != request.form.get("password2"):
            return apology("passwords must match")

        #attempts to register user, errors if one exists
        result = db.execute("insert into users (username, hash) values (:username, :hash)", username=request.form.get("username"), hash=pwd_context.encrypt(request.form.get("password")))
        if result == None:
            return apology("username already exists")
            
        # remember which user has logged in
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))
        session["user_id"] = rows[0]["id"]
        session["username"] = rows[0]["username"]

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock."""
    rows = db.execute("SELECT cash FROM users WHERE id = :id", id=session['user_id'])
    cash = rows[0]["cash"]
    if request.method == "GET":
        total = 0
        stocks = db.execute("SELECT stock, SUM(shares) AS shares, cost , symbol FROM history WHERE username = :username GROUP BY stock having SUM(Shares) > 0", username=session["username"])
        rows = db.execute("SELECT cash FROM users WHERE id = :id", id=session['user_id'])
        for stock in stocks:
            quote = lookup(stock["symbol"])
            symbol = db.execute("SELECT symbol FROM stocks WHERE symbol = :symbol", symbol=quote['symbol'])
            if db.execute("SELECT symbol FROM stocks WHERE symbol = :symbol", symbol=quote['symbol']) == 0:
                db.execute("INSERT INTO stocks (symbol, name, price) VALUES (:symbol, :name, :price)", symbol=quote['symbol'], name=quote['name'], price=quote['price'])
            else:
                db.execute("UPDATE stocks SET price = :price WHERE symbol = :symbol", price=quote['price'], symbol=quote['symbol'])
            total += int(stock['shares']) * quote['price']
            stock['cost'] = quote['price']
        cash = rows[0]["cash"]
        total = total+cash
        cash = usd(cash)
        total = usd(total)
        return render_template("sell.html", stocks=stocks, cash=cash, total=total)
    else:
        stock = request.form.get("stock")
        if stock == "Choose Stock":
            return apology("Choose a Stock")
        sell = request.form.get("shares")
        owned = db.execute("SELECT stock, SUM(shares) AS shares, cost , symbol FROM history WHERE symbol = :symbol GROUP BY stock", symbol=stock)
        sell = int(sell)
        if sell < 1:
            return apology("invalid number of shares")
        print(stock)
        if sell <= owned[0]["shares"]:
            
            #get current price of stock
            quote = lookup(stock)
            print(quote)
            #add stock to portfolio
            db.execute("INSERT INTO history (username, stock, shares, cost, symbol) VALUES (:username, :stock, :shares, :cost, :symbol)", username=session["username"], stock=quote['name'], shares=0 - sell, cost=quote['price'], symbol=request.form.get("stock").upper())
        
            #subtract cash from user
            db.execute("UPDATE users SET cash = :cash + :cost WHERE id = :id", cash=cash, cost=quote['price'] * sell, id=session["user_id"])
                
        else:
            return apology("invalid number of shares")
        return redirect(url_for("index"))

@app.route("/user", methods=["GET", "POST"])
@login_required
def user():
    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure password was submitted
        if not request.form.get("password"):
            return apology("must provide password")
            
        # ensure confirmation password was submitted
        elif not request.form.get("password2"):
            return apology("must provide confirmation password")
        
        # ensures passwords match    
        elif request.form.get("password") != request.form.get("password2"):
            return apology("passwords must match")

        #attempts to register user, errors if one exists
        result = db.execute("UPDATE users SET hash = :hash WHERE username = :username", hash=pwd_context.encrypt(request.form.get("password")), username=session["username"])

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("user.html")
    