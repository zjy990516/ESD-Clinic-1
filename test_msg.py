import json
import sys
import os
import random
import datetime
import pika
treatment={"treatment_id":"1234"
            }
def send_msg(treatment):
    hostname = 'chimpanzee-01.rmq.cloudamqp.com'
    #set the hosts for cloud amqp
    port = '5672'

    connection = pika.BlockingConnection(pika.ConnectionParameters(host=hostname,port=port))
    channel = connection.channel()

    exchangename='treatment_list'
    channel.exchange_declare(exchange=exchangename,exchange_type='direct')
    message = json.dumps(treatment,default=str)
    channel.basic_publish(exchange=exchangename,routing_key='clinic_info',body=message)
    if "treatment_id" in treatment:
        channel.queue_declare(queue='send_treatment',durable=True)
        channel.queue_bind(exchange=exchangename,queue='send_treatment',routing_key='clinic_info')
        channel.basic_publish(exchange=exchangename,routing_key='clinic_info',body=message, properties=pika.BasicProperties(delivery_mode=2))
        print("treatment send to clinic")

    connection.close()

send_msg(treatment)