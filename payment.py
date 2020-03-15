import paypalrestsdk
import logging
from paypalrestsdk import Payout, ResourceNotFound
from paypalrestsdk import Invoice
from urllib.parse import urlparse, parse_qs



paypalrestsdk.configure({
    ## merchant
  "mode": "sandbox", # sandbox or live
  "client_id": "ARiPc1IIjlwxqkCAFyBsMf8T5Z6YsxjDmU_IEmHiS8kPYw_hBt5PhzDlDqyHhI5DoYlxSWvZkWyQrLBI",
  "client_secret": "EF8H6qOQ0ZxCU3BlpuJj8roZyUDalYjtsaB6EMC1rFNZ3drIYhNTRPW4kzFP5p8Q7Hb_eFgKupVNSERq" })





from flask import Flask, request,jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

from datetime import datetime
import json
import pika

app=Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://g2t5:rootroot@esd-clinic.c6n8cu8sp46j.us-east-1.rds.amazonaws.com:3306/payment'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
CORS(app)

class Payment(db.Model):
    __tablename__ = 'payment'
    payment_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    treatment_id = db.Column(db.String,nullable=False)
    payment_date = db.Column(db.DateTime, nullable=False, default=datetime.now)
    payment_status=db.Column(db.String(10),nullable=False,default="incompleted")
    paypal_id=db.Column(db.String(20),default="0")
    price=db.Column(db.Float,nullable=False)

    def __init__(self, treatment_id, price): 
        self.treatment_id = treatment_id 
        self.price = price 
        

    def json(self):
        dto={
            'payment_id':self.payment_id,
            'treatment_id':self.treatment_id,
            'price':self.price,
            'payment_date':self.payment_date,
            'payment_status':self.payment_status,
            'paypal_id':self.paypal_id

        }
        return dto
#get data posted by treatment

@app.route("/payment")
def get_all():
    return {'payments:':[payment.json() for payment in Payment.query.all() ]}


@app.route("/payment/<string:payment_id>")
def find_payment_by_id(payment_id):
    payment=Payment.query.filter_by(payment_id=payment_id).first()
    if payment:
        return jsonify(payment.json())
    return jsonify({"message": "Payment not found."}), 404


@app.route("/createpayment",methods=['POST'])
def add_payment_to_local_database():
    treatment_id=request.json['treatment_id']
    price=request.json['price']

    payment=Payment(treatment_id=treatment_id,price=price)
    try:
        db.session.add(payment)
        db.session.commit()
    except Exception as e:
        return jsonify(
            {
                "message": "An error occurred creating the payment.",
                "error": str(e),
            }
        ), 500
    
    return jsonify(payment.json()), 201

    
#generate order(implementing paypal API)
@app.route("/paypalpayment", methods=['POST'])
def create_payment():
    treatment_id = request.json['treatment_id']
    price = request.json['price']
    status = 201
    result = {}
    print("1")
    #retrieve information  about payment and payment items from the request
    print("2")
    paypalrestsdk.configure({
        "mode": "sandbox", # sandbox or live
        "client_id": "ARiPc1IIjlwxqkCAFyBsMf8T5Z6YsxjDmU_IEmHiS8kPYw_hBt5PhzDlDqyHhI5DoYlxSWvZkWyQrLBI",
        "client_secret": "EF8H6qOQ0ZxCU3BlpuJj8roZyUDalYjtsaB6EMC1rFNZ3drIYhNTRPW4kzFP5p8Q7Hb_eFgKupVNSERq" })
    print("3")
    payment = paypalrestsdk.Payment({
        "intent": "sale",
        "payer": {
            "payment_method": "paypal"
        },
        "redirect_urls": {
            "return_url": "http://localhost:3000/payment/execute",
            "cancel_url": "http://localhost:3000/"
        },
        "transactions": [
            {
                "item_list": {
                    "items": [
                        {
                            "name":treatment_id,
                            "sku": "pet treatment",
                            "price": price,
                            "currency": "SGD",
                            "quantity":1
                        }
                    ]
                },
                "amount": {
                    "total": price,
                    "currency": "SGD"
                },
                "description": "treatment description"
            }
        ]  
    })
    print("4")
    if payment.create():
        print("5")
        try:
            #authorize the payment
            for link in payment.links:
                print("6")
                if link.rel=='approval_url':
                # Convert to str to avoid google appengine unicode issue
                # https://github.com/paypal/rest-api-sdk-python/pull/58
                    print("7")
                    approval_url = str(link.href)
                    print("Redirect for approval: %s" % (approval_url))
            status=200
            message="The payment has been created"
            result={'status':status,"message":message}
            # parsed=urlparse(approval_url)
            # ppid=parse_qs(parsed.query).get('paymentId')[0]
            # print(ppid)
            payinrds=Payment.query.filter_by(treatment_id=treatment_id).first() 
            payinrds.payment_status='Pending'
            db.session.commit()
            result['payment_info'] = payinrds.json()
        except Exception as e:
            status=500
    else:
        print("6")
        print(payment.error)
        result = {'status':500, "message":"An error occurred when creating the order in DB", "error":str(payment.error)}
    return result




@app.route('/payment/execute',methods=['GET','POST'])
def execute():
    paymentId = request.args.get('paymentId')
    payment = paypalrestsdk.Payment.find(paymentId)
    payer_id=request.args.get('PayerID')
    treatment_id=payment['transactions']['item_list']['items']['name']
    #match payer id with per parent?
    if payment.execute({"payer_id":payer_id}):
        result={'status':200,"message":"Payment execute successfully"}
        payinrds=Payment.query.filter_by(treatment_id=treatment_id).first() 
        payinrds.payment_status='Completed'
        payinrds.paypalId=paymentId
        db.session.commit()
    else:
        print(payment.error) # Error Hash
        result={'status':500,"message":payment.error}
    return result


@app.route('/payment/<int:payment_id>',methods=['PUT'])
def update_payment_status(payment_id):
    payment=Payment.query.filter_by(payment_id=payment_id)
    paymentpaypal = paypalrestsdk.Payment.find(payment_id)
    if "state" in paymentpaypal == 'Completed':
       payment.payment_status='Completed'
       date=paymentpaypal["update_time"]
       payment_date=date
       db.session.commit()
    return jsonify(payment.serialize())

# def generate_invoice(payment_id):
#     payment=Payment.query.filter_by(payment_id=payment_id)
#     paymentpaypal = paypalrestsdk.Payment.find(payment_id)
#     invoice = Invoice({
#     'merchant_info': {
#         "email": "default@merchant.com",
#     },
#     "billing_info": [{
#         "email": "example@example.com"
#     }],
#     "items": [{
#         "name": "Widgets",
#         "quantity": 20,
#         "unit_price": {
#             "currency": "USD",
#             "value": 2
#         }
#         }],
#     })

# if Invoice.create():
#     print(json.dumps(Invoice.to_dict(), sort_keys=False, indent=4))
# else:
#     print(Invoice.error)
 
if __name__ == '__main__': 
    app.run(port=3000,debug=True)