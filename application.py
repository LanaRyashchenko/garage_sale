from sql import SQL
from flask import Flask, redirect, render_template, request, session, url_for
from functools import wraps
import datetime
from passlib.apps import custom_app_context as pwd_context


app = Flask(__name__)
app.secret_key = "olalala"

 # configure CS50 Library to use SQLite database
db = SQL("sqlite:///cs50/sale.db")

def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.11/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def index():
    all_products = db.execute("SELECT items.item_picture, items.item, items.description, items.date_start, items.date_end, \
    items.max_price, items.min_price, items.days_of_sale, users.username, users.e_mail from items, users WHERE items.user_id = users.user_id \
    AND date('now') >= date_start AND date('now') <= date_end")
    price = []
    for elements in [all_products]:
        for i in elements:
            if (int(i['days_of_sale'])) > 0:
                price_per_day = round(float((i['max_price'] - i['min_price']) / int(i['days_of_sale'])), 2)
            else:
                price_per_day = round(float(i['max_price']), 2)

            current_date = str(datetime.date.today())
            current_date = current_date.split('-')
            current_date = datetime.date(int(current_date[0]),int(current_date[1]),int(current_date[2]))
     #       print(current_date)

            date_start = i['date_start']
            date_start = date_start.split('-')
            date_start = datetime.date(int(date_start[0]),int(date_start[1]),int(date_start[2]))
      #      print(date_start)

            days_after_sale_start = current_date - date_start
            days_after_sale_start = days_after_sale_start.days
            if int(days_after_sale_start) < 0:
                days_after_sale_start = 0
            current_price = round(float(i['max_price']), 2) - price_per_day * int(days_after_sale_start)
            price.append(round((current_price), 2))
            for p in price:
                i['price'] = p

    return render_template("index.html", all_products = all_products)

@app.route("/register", methods = ["POST", "GET"])
def register():
    session.clear()
    if request.method == "POST":
        if request.form["username"] == "" or request.form["password"] == "" or request.form["password_confirm"] == "" or request.form["e_mail"] == "":
            return sorry("You must provide your name and password")
        elif request.form["password"] != request.form["password_confirm"]:
            return sorry("Please, provide correct password confirmation")

        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form["username"])
        if len(rows) != 0:
            return sorry("Sorry, this user already exists")

        encrypted_hash = pwd_context.encrypt(request.form["password"])
        new_user = db.execute("INSERT INTO users (username, hash, e_mail) VALUES (:username, :hash, :e_mail)", username = request.form["username"], \
        e_mail = request.form["e_mail"], hash = encrypted_hash)
        if not new_user:
            return sorry("Sorry, this user already exists")
        else:
            session["user_id"] = new_user
            return redirect(url_for("index"))

    else:
        return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    session.clear()

    if request.method == "POST":
        if request.form["username"] == "" or request.form["password"] == "":
            return sorry("You must provide your name and password")
        else:
            rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
            return sorry("Invalid username and/or password")
        session["user_id"] = rows[0]["user_id"]

        return redirect(url_for("index"))

    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))

def sorry(s):
    return render_template("sorry.html", s=s)

#def allowed_file(filename):
#    return '.' in filename and \
#           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/lot", methods = ["POST", "GET"])
@login_required
def add_lot():
    if request.method == "POST":
        if request.form["item"] == "" or request.form["item_picture"] == "" or request.form["description"] == "" or request.form["date_start"] == "" \
        or request.form["date_end"] == "" or request.form["max_price"] == "" or request.form["min_price"] == "":
            return sorry("You must provide information about your lot")
        max_price = (request.form["max_price"])
        min_price = (request.form["min_price"])
        if not max_price.isdigit() or int(max_price) < 0:
            return sorry("Max price should be a positive number")
        elif not min_price.isdigit() or int(min_price) < 0:
            return sorry("Min price should be a positive number")
        else:
            for i in max_price.replace(',','.').split():
                max_price = round(float(i), 2)

            for m in min_price.replace(',','.').split():
                min_price = round(float(m), 2)
            if max_price < min_price:
                return sorry("Maximum price should be bigger or equal to minimum price")

            first = request.form["date_start"]
            last = request.form["date_end"]
            first = first.split('-')
            last = last.split('-')
            first_day = datetime.date(int(first[0]),int(first[1]),int(first[2]))
            last_day = datetime.date(int(last[0]),int(last[1]),int(last[2]))
            delta_days = last_day-first_day
            delta_days = delta_days.days
            if delta_days < 0:
                return sorry("Date of the end of sale should be later than the start date")
            elif delta_days == 0:
                delta_days = 1
            current = str(datetime.date.today())
            current = current.split('-')
            current_day = datetime.date(int(current[0]),int(current[1]),int(current[2]))
            check_first_date = first_day - current_day
            check_second_date = last_day - current_day

            check_first_date = check_first_date.days
            check_second_date = check_second_date.days
            if int(check_second_date) < 0 or int(check_first_date) < 0:
                return sorry("The first and the last days of sale shouldn't be past")
            new_item = db.execute("INSERT INTO items (user_id, item, description, item_picture, date_start, date_end, max_price, min_price, days_of_sale) \
            VALUES (:user_id, :item, :description, :item_picture, :date_start, :date_end, :max_price, :min_price, :days_of_sale)", \
            user_id = session["user_id"], item = request.form["item"], description = request.form["description"], \
            item_picture = request.form["item_picture"], date_start = request.form["date_start"], date_end = request.form["date_end"], \
            max_price = max_price, min_price = min_price, days_of_sale = delta_days)

            if not new_item:
                return sorry("Something went wrong")
            else:
                return redirect(url_for("my_garage"))
    return render_template("add_lot.html")

@app.route("/my_garage", methods = ["POST", "GET"])
@login_required
def my_garage():
    my_personal_info = db.execute("SELECT username, e_mail FROM users WHERE user_id = :user_id", user_id = session["user_id"])
    my_item_list = db.execute("SELECT item_picture, item, description, date_start, date_end, max_price, min_price, days_of_sale FROM\
    items WHERE user_id = :user_id", user_id = session["user_id"])
    price = []
    for elements in [my_item_list]:
        for i in elements:
            if (int(i['days_of_sale'])) > 0:
                price_per_day = round(float((i['max_price'] - i['min_price']) / int(i['days_of_sale'])), 2)
            else:
                price_per_day = round(float(i['max_price']), 2)

            current_date = str(datetime.date.today())
            current_date = current_date.split('-')
            current_date = datetime.date(int(current_date[0]),int(current_date[1]),int(current_date[2]))
     #       print(current_date)

            date_start = i['date_start']
            date_start = date_start.split('-')
            date_start = datetime.date(int(date_start[0]),int(date_start[1]),int(date_start[2]))
      #      print(date_start)

            days_after_sale_start = current_date - date_start
            days_after_sale_start = days_after_sale_start.days
            if int(days_after_sale_start) < 0:
                days_after_sale_start = 0

            current_price = round(float(i['max_price']), 2) - price_per_day * int(days_after_sale_start)
            price.append(round((current_price), 2))

            for p in price:
                i['price'] = p
       #     price = str("${0:5.2f}".format(price))
    return render_template("my_garage.html", my_personal_info = my_personal_info, my_item_list = my_item_list)

@app.route("/search", methods = ["POST", "GET"])
@login_required
def search():
    if request.method == "POST":
        if request.form["search"] == "":
            return sorry("You didn't write a word")
        else:
            word = request.form["search"]
        search_item = db.execute("\
        SELECT items.item_picture, items.item, items.description, items.date_start, items.date_end, items.max_price, items.min_price, items.days_of_sale, users.username, users.e_mail \
        FROM items, users \
        WHERE items.user_id = users.user_id AND date('now') >= date_start AND date('now') <= date_end AND (items.description || items.item) LIKE :word", word="%" + str(word) + "%")
        if not search_item:
            return sorry("No results")
        else:
            price = []
            for elements in [search_item]:
                for i in elements:
                    if (int(i['days_of_sale'])) > 0:
                        price_per_day = round(float((i['max_price'] - i['min_price']) / int(i['days_of_sale'])), 2)
                    else:
                        price_per_day = round(float(i['max_price']), 2)

                current_date = str(datetime.date.today())
                current_date = current_date.split('-')
                current_date = datetime.date(int(current_date[0]),int(current_date[1]),int(current_date[2]))

                date_start = i['date_start']
                date_start = date_start.split('-')
                date_start = datetime.date(int(date_start[0]),int(date_start[1]),int(date_start[2]))

                days_after_sale_start = current_date - date_start
                days_after_sale_start = days_after_sale_start.days
                if int(days_after_sale_start) < 0:
                    days_after_sale_start = 0
                current_price = round(float(i['max_price']), 2) - price_per_day * int(days_after_sale_start)
                price.append(round((current_price), 2))
                for p in price:
                    i['price'] = p
            return result(search_item)
    else:
        return render_template("search.html")

@app.route("/result", methods = ["POST", "GET"])
@login_required
def result(search_item):
    return render_template("result.html", search_item = search_item)

if __name__ == '__main__':
    app.run()