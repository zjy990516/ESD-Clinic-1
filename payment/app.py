from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import json

import pika

import paypalrestsdk
import logging
from paypalrestsdk import Payout, ResourceNotFound
from paypalrestsdk import Invoice

app=Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://clinic_db_user:rootroot@localhost:3306/payment'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
CORS(app)

paypalrestsdk.configure(
    {
        ## merchant
        "mode": "sandbox", # sandbox or live
        "client_id": "ARiPc1IIjlwxqkCAFyBsMf8T5Z6YsxjDmU_IEmHiS8kPYw_hBt5PhzDlDqyHhI5DoYlxSWvZkWyQrLBI",
        "client_secret": "EF8H6qOQ0ZxCU3BlpuJj8roZyUDalYjtsaB6EMC1rFNZ3drIYhNTRPW4kzFP5p8Q7Hb_eFgKupVNSERq" 
    }
)

@app.route("/payment/all", methods=['GET'])
def get_all():
    return {'payments:':[payment.json() for payment in Payment.query.all() ]}


@app.route("/payment/paymemt_id")
def find_payment_by_id(payment_id):
    payment = payment.query.filter_by(payment_id = payment_id).first()
    if payment:
        return payment.json()
    return jsonify({"message": "Payment not found."}), 404


#generate order(implementing paypal API)
@app.route("/payment/<string:payment_id>", methods=['POST'])
def create_payment(payment_id):
    step_count = 0
    try:
        print("step {step}: processing new payment".format(step = step_count))
        # 1 retrieve information  about payment and payment items from the request
        step_count += 1
        try: 
            treatment_id = request.json['treatment_id']
            price = request.json['price']
            status = 201
            result = {}
            print("step {step}: get payment data: treatment_id => {t_id}, price => {price}".format(step = step_count, t_id = treatment_id, price = price))
        except Exception as e:
            result = {
                'status':400, 
                "message":"An error occurred when retrieving 'treatment_id' and 'price' from request", 
                "error":str(e)
            }
            print("An error occured in step {step}".format(step = step_count))
            return (result)
        
        # 2 Creating PayPal Payment Obj    
        step_count += 1
        try:
            print("step {step}: processing new payment".format(step = step_count))
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
                                    "treatment": treatment_id,
                                    "sku": "item",
                                    "price": price,
                                    "currency": "SGD",
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
        except Exception as e:
            result = {
                'status':500, 
                "message":"Can not create PayPal payment Obj, please see error for detail", 
                "error":str(e)
            }
            print("An error occured in step {step}".format(step = step_count))
            return (result)

        # 3 Update new payment to database 
        step_count += 1
        if payment.create():
            try:
                print("step {step}: processing new payment".format(step = step_count))
                #authorize the payment
                for link in payment.links:
                    if link.rel=='approval_url':
                    # Convert to str to avoid google appengine unicode issue
                    # https://github.com/paypal/rest-api-sdk-python/pull/58
                        approval_url = str(link.href)
                        print("Treatment: {1} linked to redirect url for approval: {0}".format(approval_url, treatment_id))
                        # Creating Payment for DB insertion 
                        curr_payment = Payment(treatment_id = treatment_id, price = price, pay_url = approval_url)
                        db.session.add(curr_payment)
                        # Insert payment record into DB
                        db.session.commit()

                status=200
                message="Payment:(linked with treatment:{0}) has been created".format(treatment_id)
                result={'status':status,"message":message}
            except Exception as e:
                status=500
        else:
            print("An error occured in step {step}:".format(step = step_count))
            print(payment.error)
            result = {
                'status':500, 
                "message":"An error occurred when creating PayPal Payment Obj", 
                "error":str(payment.error)
            }
        return result
    except Exception as e: 
        status = 500
        result={'status':500,"message":payment.error}
        return result


@app.route('/paymentupdate/<int:payment_id>', methods = ['POST'])
def payment_execute(payment_id):
    print("Executing payment_execute with payment_id: {0};".format(payment_id))
    #find a payment
    try:    
        payment = paypalrestsdk.Payment.find(payment_id)
        #match payer id with per parent?
        payer_id = request.json['payer_id']
        if payment.execute({"payer_id":payer_id}):
            # received money 
            result={'status':200,"message":"Payment execute successfully"}
        else:
            # got some error
            print(payment.error) # Error Hash
            result={'status':500,"message":payment.error}
        return result
    except Exception as e: 
        status = 500
        result={'status':500,"message":str(e)}
        return result


@app.route('/payment/<int:payment_id>',methods=['PUT'])
def update_payment_status(payment_id):
    payment = Payment.query.filter_by(payment_id=payment_id)

    paymentpaypal = paypalrestsdk.Payment.find(payment_id)

    if "state" in paymentpaypal == 'Completed':
       payment.payment_status = 'Completed'
       date = paymentpaypal["update_time"]
       payment_date = date
       db.session.commit()
    return jsonify(payment.serialize())

def update_payment_status(payment_id, payment_status, ):
    self.treatment_id = treatment_id 
    self.price = price 
    self.pay_url = pay_url
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
    app.run(host='0.0.0.0', port=5000, debug=True)