import datetime
import jwt
from .transaction import Transaction
SECRET_KEY = "b'|\xe7\xbfU3`\xc4\xec\xa7\xa9zf:}\xb5\xc7\xb9\x139^3@Dv'"

#--------------------------------Stats----------------------------------

def getStatsDate(dates,rates,time):
    statsCurr = {}
    dateCurr = datetime.datetime.now() - datetime.timedelta(hours=time)
    unit=''
    if (time>24):
        unit="d"
        displaytime=int(time/24)
    else:
        unit="h"
        displaytime=time

    for i in range(len(dates)):
        if dates[i] <= dateCurr:  # we found the first rate that was calculated for earlier than one hour from api call time
            if (i==0):#here that means that no change was made one hour from that api call since the dates are now sorted in decreasing order
                statsCurr[str(displaytime)+unit]=0
                break
            else:
                change1 = ((rates[0]-rates[i]) / rates[i]) * 100  # in %
                statsCurr[str(displaytime)+unit] = round(change1, 2)
                break
        if i == len(dates) - 1:  # this means that all transactions of this type were calculated later than  1hour  before the time the api was called
            # in this case, calculate change between most recent and oldest rate
            change1 = ((rates[0]-rates[i]) / rates[i]) * 100  # in %
            statsCurr[str(displaytime)+unit] = round(change1, 2)
            break
    return statsCurr



def get_rate_graph(Sell):
    # get all transactions where we sell usd sorted by date added
    transactions = Transaction.query.filter_by(usd_to_lbp=Sell)
    count = 0  # to know how many transactions have been stored
    rates = []  # array of avg rates up until matching date at same index in date array
    dates = []  # array of dates
    cumu = 0  # to store cumulative sum of avg rates up until a date
    for trans in transactions:
        count += 1
        cumu += trans.lbp_amount / trans.usd_amount
        avg = cumu / count
        rates.append(round(avg, 3))
        dates.append(trans.added_date)
    data = {"x": dates, "y": rates}
    return data

#--------------------------------Token----------------------------------

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

