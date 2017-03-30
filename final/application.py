from RiotAPI import RiotAPI
import requests
import RiotConsts as Consts
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import gettempdir
import time
import json

from helpers import *

#myid 76052556

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


# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = gettempdir()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///league.db")

#set api_key
api = RiotAPI(Consts.API_KEY['key'])

#load champs
def get_champ():
    url = Consts.DATA['champs']
    r = requests.get(url).json()
    s = r["data"]
    return s
champs = get_champ()
champ_id = {}
for champ in champs:
    champ_id[champs[champ]['key']] = champ
    
#time converter
def convert_time(timestamp):
    a = time.strftime("%a %d %b %Y %I:%M%p", time.localtime((timestamp / 1000.0) - 14540))
    return a
    
def game_length(seconds):
    s = time.strftime("%M:%S", time.gmtime(seconds))
    return s
    
#champ image
def champ_image(name):
    a = "http://ddragon.leagueoflegends.com/cdn/6.24.1/img/champion/"+name+".png"
    return a
    
#champ background
def champ_background(name):
    a = "http://ddragon.leagueoflegends.com/cdn/img/champion/splash/"+name+"_0.jpg"
    return a
    
#item pngs
def item_icon(item):
    url = Consts.URL['item by id'].format(
        url=item
        )
    return url
    
#summoner spells
def sum_spell(spell_id):
    url = Consts.SUMS[str(spell_id)]
    return url

#game type
def game_type(game):
    r = Consts.GAMES[game]
    return r
    
#row color
def row_color(win):
    if win is True:
        r = '#6EEE59'
    else:
        r = '#F86C6C'
    return r
    
#KDA Calculator
def kda_score(kills, deaths, assists):
    k = kills
    d = deaths
    a = assists
    if not k:
        k = '0'
    if not d :
        d = '0'
    if not a:
        a = '0'
    k = str(k)
    d = str(d)
    a = str(a)
    r = k+'/'+d+'/'+a
    return r
    
#setup item list
def item_url(match):
    array = []
    for i in range(6):
        try:
            item = match['stats']['item'+str(i)]
            array.append(item_icon(item))
        except:
            None
    return array
        
    
#session setup
def session_info(rows):
    session["user_id"] = rows[0]["id"]
    session["username"] = rows[0]["username"]
    r = api.get_summoner_by_name(rows[0]["summoner"])
    name = rows[0]["summoner"]
    id_num = r[name.lower()]['id']
    id_num = str(id_num)
    league = api.get_league(id_num)
    session["summoner"] = r[name.lower()]['name']
    session["id"] = id_num
    session["level"] = r[name.lower()]['summonerLevel']
    session["league"] = league[id_num][0]['tier']
    session["division"] = league[id_num][0]['entries'][0]['division']
    session["lp"] = league[id_num][0]['entries'][0]['leaguePoints']
    
#most command champion for background html
def most_common(lst):
    return max(set(lst), key=lst.count)

app.jinja_env.globals.update(champ_background=champ_background)
app.jinja_env.globals.update(kda_score=kda_score)
app.jinja_env.globals.update(row_color=row_color)
app.jinja_env.globals.update(game_type=game_type)
app.jinja_env.globals.update(champ_image=champ_image)
app.jinja_env.globals.update(convert_time=convert_time)
app.jinja_env.globals.update(sum_spell=sum_spell)
app.jinja_env.globals.update(item_icon=item_icon)
app.jinja_env.globals.update(item_url=item_url)
app.jinja_env.globals.update(game_length=game_length)
        

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method=="POST":
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=session["username"])
        session_info(rows)
        m = api.get_matches(session["id"])
        submit = request.form.get('submit')
        comment = request.form.get(str(submit))
        matches = m["games"]
        champs = []
        for match in matches:
            champs.append(match['championId'])
        a = most_common(champs)
        print(matches[int(submit)]['createDate'])
        db.execute("INSERT INTO notes (user_id, match, comments, date) VALUES (:user_id, :match, :comments, :date)", user_id=session["user_id"], match=json.dumps(matches[int(submit)]), comments=comment, date=matches[int(submit)]['createDate'])
        return render_template("index.html", matches=matches, champ_id=champ_id, a=a)
    else:
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=session["username"])
        session_info(rows)
        m = api.get_matches(session["id"])
        matches = m["games"]
        champs = []
        for match in matches:
            champs.append(match['championId'])
        a = most_common(champs)
        return render_template("index.html", matches=matches, champ_id=champ_id, a=a)
        
@app.route("/login", methods=["GET","POST"])
def login():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":


        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
            return render_template("login.html", error="Invalid Username or Password")

        # remember which user has logged in
        session_info(rows)

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Registers a user."""
    
    # forget any user_id
    session.clear()
    
    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        #checks to see if user exists
        result = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))
        if result:
            return render_template("register.html", error = "Username already exists")
        
        #add user to database
        db.execute("insert into users (username, hash, summoner) values (:username, :hash, :summoner)", username=request.form.get("username"), hash=pwd_context.encrypt(request.form.get("password")), summoner=request.form.get("summoner"))
        # remember which user has logged in
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))
        session_info(rows)

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")
        
@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))

@app.route("/user", methods=["GET", "POST"])
@login_required
def user():
    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=session["username"])
        session_info(rows)
        #attempts to register user, errors if one exists
        result = db.execute("UPDATE users SET hash = :hash WHERE username = :username", hash=pwd_context.encrypt(request.form.get("password")), username=session["username"])

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=session["username"])
        session_info(rows)
        return render_template("user.html")

@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method=="POST":
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=session["username"])
        session_info(rows)
        name = request.form.get('summoner')
        name = name.replace(" ", "")
        r = api.get_summoner_by_name(name.lower())
        id_num = r[name.lower()]['id']
        m = api.get_matches(id_num)
        matches = m["games"]
        champs = []
        for match in matches:
            champs.append(match['championId'])
        a = most_common(champs)
        return render_template("searched.html", matches=matches, champ_id=champ_id, a=a)
    else:
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=session["username"])
        session_info(rows)
        return render_template("search.html")
        
@app.route("/notes", methods=["GET", "POST"])
@login_required
def notes():
    if request.method=="POST":
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=session["username"])
        session_info(rows)
        return render_template("notes.html")
    else:
        info = db.execute("SELECT * FROM users WHERE username = :username", username=session["username"])
        session_info(info)
        rows = db.execute("SELECT * FROM notes where user_id = :user_id order by date DESC", user_id=session["user_id"])
        if not rows:
            return redirect(url_for("index"))
        else:
            print(rows)
            datas = []
            matches = []
            for row in rows:
                datas.append(row['match'])
            champs = []
            for data in datas:
                data = json.loads(data)
                matches.append(data)
            for match in matches:
                champs.append(match['championId'])
            a = most_common(champs)
            return render_template("notes.html", matches=matches, rows=rows, champ_id=champ_id, a=a)