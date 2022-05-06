from ..app import db, ma, bcrypt

class User(db.Model):
    def __init__(self, user_name, password):
        super(User, self).__init__(user_name=user_name)
        self.hashed_password = bcrypt.generate_password_hash(password)
        self.usdAmount=0
        self.lbpAmount=0
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(30), unique=True)
    hashed_password = db.Column(db.String(128))
    usdAmount = db.Column(db.Integer())
    lbpAmount = db.Column(db.Integer())
class UserSchema(ma.Schema):
    class Meta:
        fields = ("id", "user_name","usdAmount","lbpAmount")
        model = User