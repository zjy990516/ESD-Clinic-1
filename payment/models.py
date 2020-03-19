from app import db 
import datetime

class Payment(db.Model):
    __tablename__ = 'payment'
    payment_id = db.Column(db.Integer, primary_key=True)
    treatment_id = db.Column(db.Integer, db.ForeignKey('treatment_id'),nullable=False)
    payment_date = db.Column(db.DateTime, nullable=False, default=datetime.now)
    payment_status = db.Column(db.String(10),nullable=False, default="incompleted")
    pay_url = db.Column(db.String(150),nullable=False, default="incompleted")
    price=db.Column(db.Float,nullable=False)

    def __init__(self, treatment_id, price):
        self.treatment_id = treatment_id 
        self.price = price 
        self.pay_url = pay_url

    def json(self):
        dto={
            'payment_id':self.payment_id,
            'treatment_id':self.treatment_id,
            'price':self.price,
            'payment_date':self.payment_date,
            'payment_status':self.payment_status,
            'pay_url': self.pay_url
        }
        return dto