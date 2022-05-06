from ..app import db, ma
import datetime

class Post(db.Model):
    def __init__(self, user_id, usd_amount, lbp_amount, typeSell):
        super(Post, self).__init__(
        user_id=user_id,
        usd_amount=usd_amount,
        lbp_amount=lbp_amount,
        typeSell=typeSell,
        added_date=datetime.datetime.now())

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'),nullable=True)
    usd_amount = db.Column(db.Float)
    lbp_amount = db.Column(db.Float)
    typeSell = db.Column(db.Boolean)
    added_date = db.Column(db.DateTime)


class PostSchema(ma.Schema):
    class Meta:
        fields = ("id", "user_id", "usd_amount", "lbp_amount", "typeSell", "added_date")
        model = Post