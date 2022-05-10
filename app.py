from flask import Flask, request, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc, asc, delete
from flask_cors import CORS
from flask_marshmallow import Marshmallow
from flask_bcrypt import Bcrypt
import jwt
import datetime

DB_CONFIG = 'mysql+pymysql://root:rootroot@127.0.0.1:3306/exchange'

SECRET_KEY = "b'|\xe7\xbfU3`\xc4\xec\xa7\xa9zf:}\xb5\xc7\xb9\x139^3@Dv'"

app = Flask(__name__)
ma = Marshmallow(app)
bcrypt = Bcrypt(app)

app.config['SQLALCHEMY_DATABASE_URI'] = DB_CONFIG
CORS(app)
db = SQLAlchemy(app)

from .model.user import User, UserSchema
from .model.transaction import Transaction, TransactionSchema
from .model.post import Post, PostSchema
from .model.functions import *

transaction_schema = TransactionSchema()
transaction_schemaL = TransactionSchema(many=True)
user_schema = UserSchema()
post_schema = PostSchema()


# db.create_all()


@app.route('/transaction', methods=['POST'])
def addTransaction():
    tkn = extract_auth_token(request)
    r1 = request.json["usd_amount"]
    r2 = request.json["lbp_amount"]
    r3 = request.json["usd_to_lbp"]
    if (tkn == None):
        txn = Transaction(r1, r2, r3, None)
        db.session.add(txn)
        db.session.commit()
        return jsonify(transaction_schema.dump(txn))
    else:
        try:
            txn = Transaction(r1, r2, r3, decode_token(tkn))
            db.session.add(txn)
            db.session.commit()
            return jsonify(transaction_schema.dump(txn))
        except Exception:
            abort(403)


@app.route('/transaction', methods=['GET'])
def getTransactions():
    tkn = extract_auth_token(request)
    if (tkn == None):
        abort(403)
    else:
        try:
            userid = decode_token(tkn)
            query = Transaction.query.filter_by(user_id=userid)
            return jsonify(transaction_schemaL.dump(query))

        except Exception:
            abort(403)


@app.route('/exchangeRate', methods=['GET'])
def getRates():
    endTime = datetime.datetime.now()
    startTime = endTime - datetime.timedelta(days=3)
    sellUsdTransactions = Transaction.query.filter(
        Transaction.added_date.between(startTime, endTime),
        Transaction.usd_to_lbp == True).all()

    buyUsdTransactions = Transaction.query.filter(
        Transaction.added_date.between(startTime, endTime),
        Transaction.usd_to_lbp == False).all()

    sellRates = []
    buyRates = []
    for txn in sellUsdTransactions:
        sellRates.append(txn.lbp_amount / txn.usd_amount)
    for txn in buyUsdTransactions:
        buyRates.append(txn.lbp_amount / txn.usd_amount)
    if (len(sellRates) != 0):
        sellRate = sum(sellRates) / len(sellRates)
        sellRate = round(sellRate, 2)
    else:
        sellRate = None
    if (len(buyRates) != 0):
        buyRate = sum(buyRates) / len(buyRates)
        buyRate = round(buyRate, 2)
    else:
        buyRate = None
    return jsonify(usd_to_lbp=sellRate, lbp_to_usd=buyRate)


@app.route('/user', methods=['POST'])
def addUser():
    username = request.json["user_name"]
    password = request.json["password"]
    usr = User(username, password)
    db.session.add(usr)
    db.session.commit()
    return jsonify(user_schema.dump(usr))


@app.route('/authentication', methods=['POST'])
def getAuth():
    username = request.json["user_name"]
    password = request.json["password"]
    if (username == None or password == None or username == "" or password == ""):
        abort(400)

    query = User.query.filter_by(user_name=username).first()
    if (query == None):
        abort(403)

    if (not bcrypt.check_password_hash(query.hashed_password, password)):
        abort(403)

    tkn = create_token(query.id)

    return jsonify(token=tkn)



@app.route('/post', methods=['POST'])
def addPost():
    tkn = extract_auth_token(request)
    r1 = request.json["usd_amount"]
    r2 = request.json["lbp_amount"]
    r3 = request.json["typeSell"]
    if (tkn == None):
        return
    else:
        try:
            post = Post(decode_token(tkn), r1, r2, r3)
            db.session.add(post)
            db.session.commit()
            return jsonify(post_schema.dump(post))
        except Exception:
            abort(403)


# api to delete post once completed
@app.route('/acceptPost', methods=['POST'])
def acceptPost():
    postid = request.json["postid"]
    post = Post.query.filter_by(id = postid).first()
    if post is None:
        return
    tkn = extract_auth_token(request)
    r1 = post.usd_amount
    r2 = post.lbp_amount
    r3 = post.typeSell
    Post.query.filter(Post.id == postid).delete()
    try:
        txn = Transaction(r1, r2, r3, decode_token(tkn))
        db.session.add(txn)
        db.session.commit()
        return jsonify(transaction_schema.dump(txn))
    except Exception:
        abort(403)



@app.route('/getPosts', methods=['GET'])
def getPosts():
    tkn = extract_auth_token(request)
    useridCurr = decode_token(tkn)
    if (tkn == None):
        return
    posts = Post.query.filter(Post.user_id != useridCurr).order_by(asc(Post.added_date)).all()
    postsArr = []
    data = {}
    for post in posts:
        user = User.query.filter_by(id=post.user_id).first()
        dataPost = {"id": post.id, "user_id": post.user_id, "username": user.user_name,
                    "usd_amount": post.usd_amount, "lbp_amount": post.lbp_amount,
                    "typeSell": post.typeSell, "added_date": post.added_date
                    }
        postsArr.append(dataPost)
    return jsonify(postsArr)






# api to get statistics about rate changes of buying usd
# change in last 24 hours/
@app.route('/getstatbuy', methods=['GET'])
def get_stats_buy():
    data = get_rate_graph(False)

    dates = data['x']  # easier to start from last rate since we need to go backwards
    rates = data['y']
    dates.reverse()
    rates.reverse()
    stats = {}  # returned dictionary
    # first get current time when the api is called, since we need to compare rates from the time the api was called
    # we need to give the changes in, for example, the last 12 hours FROM THE TIME THE API HAS BEEN CALLED
    stats.update(getStatsDate(dates, rates, 1))
    stats.update(getStatsDate(dates, rates, 12))
    stats.update(getStatsDate(dates, rates, 24))
    stats.update(getStatsDate(dates, rates, 168))
    stats["max"] = max(rates)  # max rate ever
    stats["min"] = min(rates)  # min rate ever
    return jsonify(stats)


# api to get statistics about rate changes of selling usd
@app.route('/getstatsell', methods=['GET'])
def get_stats_sell():
    data = get_rate_graph(True)
    dates = data['x']  # easier to start from last rate since we need to go backwards
    rates = data['y']
    dates.reverse()
    rates.reverse()
    stats = {}  # returned dictionary
    # first get current time when the api is called, since we need to compare rates from the time the api was called
    # we need to give the changes in, for example, the last 12 hours FROM THE TIME THE API HAS BEEN CALLED
    stats.update(getStatsDate(dates, rates, 1))
    stats.update(getStatsDate(dates, rates, 12))
    stats.update(getStatsDate(dates, rates, 24))
    stats.update(getStatsDate(dates, rates, 168))
    stats["max"] = max(rates)  # max rate ever
    stats["min"] = min(rates)  # min rate ever
    return jsonify(stats)


# api that returns json with 3 fields: x coordinates(dates of rates) y1/y2: avg rate up to the corresponding date FOR SELLING/buying USD TO LBP
@app.route('/getgraph', methods=['GET'])
def graph():
    B = Transaction.query.filter_by(usd_to_lbp=False)
    S = Transaction.query.filter_by(usd_to_lbp=True)
    dsell = []
    rsell = []
    dbuy = []
    rbuy = []

    for i in B:
        dbuy.append(i.added_date)
        rbuy.append(i.lbp_amount / i.usd_amount)
    for i in S:
        dsell.append(i.added_date)
        rsell.append(i.lbp_amount / i.usd_amount)

    # get min date
    if dsell[0] <= dbuy[0]:
        startd = dsell[0]
    else:
        startd = dbuy[0]
    # get max date
    if dsell[len(dsell) - 1] >= dbuy[len(dbuy) - 1]:
        endd = dsell[len(dsell) - 1]
    else:
        endd = dbuy[len(dbuy) - 1]

    daycount = (endd - startd).days + 1  # hom many days to consider
    start = datetime.datetime(year=startd.year, month=startd.month, day=startd.day)

    dates = []
    buy = []
    sell = []
    di = 0
    si = 0
    cumuS = 0
    cumuB = 0
    countS = 0
    countB = 0
    for i in range(daycount + 1):
        currdate = start + datetime.timedelta(days=1)
        dates.append(str(start.day) + '-' + str(start.strftime("%B")))

        while di < len(dbuy) and dbuy[di] < currdate:
            cumuB += rbuy[di]
            countB += 1
            di += 1
        if (countB == 0):
            if (len(buy) == 0):
                buy.append(0)
            else:
                buy.append(buy[len(buy) - 1])
        else:
            buy.append(round(cumuB / countB, 3) / 1000)

        while si < len(dsell) and dsell[si] < currdate:
            cumuS += rsell[si]
            countS += 1
            si += 1
        if (countS == 0):
            if (len(sell) == 0):
                sell.append(0)
            else:
                sell.append(sell[len(sell) - 1])
        else:
            sell.append(round(cumuS / countS, 3) / 1000)
        start = start + datetime.timedelta(days=1)
    data = {}
    data["x"] = dates
    data["buy"] = buy
    data["sell"] = sell

    return jsonify(data)
