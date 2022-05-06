from flask import Flask, request, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc
from flask_cors import CORS
from flask_marshmallow import Marshmallow
from flask_bcrypt import Bcrypt
import jwt
import datetime


DB_CONFIG=DBCONFIG='mysql+pymysql://root:root@127.0.0.1:5000/exchange'

SECRET_KEY = "b'|\xe7\xbfU3`\xc4\xec\xa7\xa9zf:}\xb5\xc7\xb9\x139^3@Dv'"

app = Flask(__name__)
ma = Marshmallow(app)
bcrypt = Bcrypt(app)

app.config['SQLALCHEMY_DATABASE_URI'] = DB_CONFIG
CORS(app)
db = SQLAlchemy(app)

from .model.user import User, UserSchema
from .model.transaction import Transaction, TransactionSchema

from .model.post import Post,PostSchema
post_schema=PostSchema()
#db.create_all()
@app.route('/hello', methods=['GET'])
def hello_world():
    return "Hello World!"

@app.route('/transaction', methods=['POST'])
def addTransaction():
    tkn = extract_auth_token(request)
    r1 = request.json["usd_amount"]
    r2 = request.json["lbp_amount"]
    r3 = request.json["usd_to_lbp"]
    if (tkn == None):
        txn = Transaction(r1,r2,r3,None)
        db.session.add(txn)
        db.session.commit()
        return jsonify(transaction_schema.dump(txn))
    else:
        try:
            txn = Transaction(r1,r2,r3,decode_token(tkn))
            db.session.add(txn)
            db.session.commit()
            return jsonify(transaction_schema.dump(txn))
        except Exception:
            abort(403)
        
@app.route('/transaction',methods=['GET'])
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
        Transaction.added_date.between(startTime,endTime),
        Transaction.usd_to_lbp == True).all()

    buyUsdTransactions = Transaction.query.filter(
        Transaction.added_date.between(startTime,endTime),
        Transaction.usd_to_lbp == False).all()

    sellRates = []
    buyRates = []
    for txn in sellUsdTransactions:
        sellRates.append(txn.lbp_amount/txn.usd_amount)
    for txn in buyUsdTransactions:
        buyRates.append(txn.lbp_amount/txn.usd_amount)
    if (len(sellRates)!=0):
        sellRate = sum(sellRates)/len(sellRates)
        sellRate = round(sellRate,2)
    else:
        sellRate = None
    if(len(buyRates)!=0):
        buyRate = sum(buyRates)/len(buyRates)
        buyRate = round(buyRate,2)
    else:
        buyRate = None
    return jsonify(usd_to_lbp=sellRate,lbp_to_usd=buyRate)


@app.route('/user', methods=['POST'])
def addUser():
    username = request.json["user_name"]
    password = request.json["password"]
    usr = User(username,password)
    db.session.add(usr)
    db.session.commit()
    return jsonify(user_schema.dump(usr))


@app.route('/authentication')
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
#api to add funds to user wallet. Needs: token,funds to add :['USD' or 'LBP'] and amount to add
@app.route('/addfunds',methods=['POST'])
def add_funds():
    tkn = extract_auth_token(request)
    if (tkn == None):
        abort(403)

    else:
        try:
            userid = decode_token(tkn)
            user = User.query.filter_by(id=userid).first()
            type=request.json['type']
            amount=request.json['amount']
            if type=='USD':
                user.usdAmount += amount
            else:
                user.lbpAmount+=amount
            db.session.commit()
            return jsonify(user_schema.dump(user))
        except Exception:
            abort(403)
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
            post = Post(decode_token(tkn),r1,r2,r3)
            db.session.add(post)
            db.session.commit()
            return jsonify(post_schema.dump(post))
        except Exception:
            abort(403)

@app.route('/getPosts', methods=['GET'])
def getPosts():
    pass

#api to get user funds excepts token
#returns json {"USD":amount,"LBP":amount}
@app.route('/getfunds',methods=['GET'])
def get_funds():
    tkn = extract_auth_token(request)
    if (tkn == None):
        abort(403)

    else:
        try:
            userid = decode_token(tkn)
            user = User.query.filter_by(id=userid).first()

            return jsonify({"USD":user.usdAmount,"LBP":user.lbpAmount})
        except Exception:
            abort(403)

#api that returns json with 2 fields: x coordinates(dates of rates) y: avg rate up to the corresponding date FOR SELLING USD TO LBP
@app.route('/getgraphsell',methods=['GET'])
def get_rate_graph_buy():
    #get all transactions where we sell usd sorted by date added
    transactions=Transaction.query.filter_by(usd_to_lbp=True)
    count = 0

    rates=[]
    dates=[]
    cumu=0
    for trans in transactions:
        count+=1
        cumu+=trans.lbp_amount/trans.usd_amount
        avg=cumu/count
        rates.append(round(avg,3))
        dates.append(trans.added_date)
    data = {"x":dates,"y":rates}
    return jsonify(data)


#api that returns json with 2 fields: x coordinates(dates of rates) y: avg rate up to the corresponding date FOR SELLING USD TO LBP
@app.route('/getgraphbuy',methods=['GET'])
def get_rate_graph_sell():
    #get all transactions where we sell usd sorted by date added
    transactions=Transaction.query.filter_by(usd_to_lbp=False)
    count = 0

    rates=[]
    dates=[]
    cumu=0
    for trans in transactions:
        count+=1
        cumu+=trans.lbp_amount/trans.usd_amount
        avg=cumu/count
        rates.append(round(avg,3))
        dates.append(trans.added_date)
    data = {"x":dates,"y":rates}
    return jsonify(data)

transaction_schema = TransactionSchema()
transaction_schemaL = TransactionSchema(many=True)

user_schema = UserSchema()


def create_token(user_id):
    payload = {
    'exp': datetime.datetime.utcnow() + datetime.timedelta(days=4),
    'iat': datetime.datetime.utcnow(),
    'sub': user_id
    }
    return jwt.encode(
    payload,
    SECRET_KEY,
    algorithm='HS256'
    )

def extract_auth_token(authenticated_request):
    auth_header = authenticated_request.headers.get('Authorization')
    if auth_header:
        return auth_header.split(" ")[1]
    else:
        return None
def decode_token(token):
    payload = jwt.decode(token, SECRET_KEY, 'HS256')
    return payload['sub']



