import paypalrestsdk
import logging
from paypalrestsdk import Payout, ResourceNotFound
from paypalrestsdk import Invoice


paypalrestsdk.configure({
    ## merchant
  "mode": "sandbox", # sandbox or live
  "client_id": "AbuiDmqZ1ws36c63l4vTwBEtr9hjsKyGFGJJixKmsjOpMg554FboAQXi7oGFsEFOah3GNBYgkjzLmede",
  "client_secret": "EEHSsxKZ59WJcecaZQWKvzUkhyD210AothEdoYOBOjBrEO29IR0fzW2nlwuZN2DGTYt44yGaT_9EwU7p" })

from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

from datetime import datetime
import json
import pika

app=Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://[username]:[password]@[hostname]:[port]/[database_name]' 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db=SQLAlchemy(app)
CORS(app)

db=SQLAlchemy(app)

#communication patterns:



class Payment(db.Model):
    __tablename__ = 'payment'
    payment_id = db.Column(db.Integer, primary_key=True)
    treatment_id = db.Column(db.Integer, db.ForeignKey('treatment_id'),nullable=False)
    payment_date = db.Column(db.DateTime, nullable=False, default=datetime.now)
    payment_status=db.Column(db.String(10),nullable=False,default="incompleted")
    price=db.Column(db.Float,nullable=False)

    
    def json(self):
        dto={
            'payment_id':self.payment_id,
            'treatment_id':self.treatment_id,
            'price':self.price,
            'payment_date':self.payment_date,
            'payment_status':self.payment_status,

        }
        return dto
#get data posted by treatment

@app.route("/payment_id")
def get_all():
    return {'payments:':[payment.json() for payment in Payment.query.all() ]}


@app.route("/payment/paymemt_id")
def find_payment_by_id(payment_id):
    payment=payment.query.filter_by(payment_id=payment_id).first()
    if payment:
        return payment.json()
    return jsonify({"message": "Payment not found."}), 404


#generate order(implementing paypal API)
@app.route("/payment/<string:payment_id>",methods=['POST'])
def create_payment(payment_id):
    treatment_id=request.json['treatment_id']
    price=request.json['price']
    status=201
    result={}

    #retrieve information  about payment and payment items from the request
    
    payment = Payment(treatment_id=treatment_id,price=price)
    
    paypalrestsdk.configure({
        "mode": "sandbox", # sandbox or live
        "client_id": "ARiPc1IIjlwxqkCAFyBsMf8T5Z6YsxjDmU_IEmHiS8kPYw_hBt5PhzDlDqyHhI5DoYlxSWvZkWyQrLBI",
        "client_secret": "EF8H6qOQ0ZxCU3BlpuJj8roZyUDalYjtsaB6EMC1rFNZ3drIYhNTRPW4kzFP5p8Q7Hb_eFgKupVNSERq" })

    payment = paypalrestsdk.Payment({
        "intent": "sale",
        "payer": {
            "payment_method": "paypal"},
        "redirect_urls": {
            "return_url": "http://localhost:3000/payment/execute",
            "cancel_url": "http://localhost:3000/"},
        "transactions": [{
            "item_list": {
                "items": [{
                    "treatment": treatment_id,
                    "sku": "item",
                    "price": price,
                    "currency": "SGD",
                    }]},
            "amount": {
                "total": price,
                "currency": "SGD"},
            "description": treatment.description}]})

    if payment.create():
        try:
            #authorize the payment
            for link in payment.links:
                if link.rel=='approval_url':
                # Convert to str to avoid google appengine unicode issue
                # https://github.com/paypal/rest-api-sdk-python/pull/58
                    approval_url = str(link.href)
                    print("Redirect for approval: %s" % (approval_url))
                    db.session.add(payment)
                    db.session.commit()
        except Exception as e:
            status=500
    else:
        print(payment.error)
        result = {'status':500, "message":"An error occurred when creating the order in DB", "error":str(payment.error)}

       
def execute_payment(payment_id):
    payment = paypalrestsdk.Payment.find(payment_id)
    result={}
    #match payer id with per parent?
    if payment.execute({"payer_id":payer_id}):
        result={'status':200,"message":"Payment execute successfully"}
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
    app.run(port=5000,debug=True)