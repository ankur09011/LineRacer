import json
import pika

from helpers import get_intersection


connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))

channel = connection.channel()

channel.exchange_declare(exchange='race',
                         exchange_type='direct')


line1 = {"slope" : 5.5,
         "intcpt" : 2}

line2 = {"slope" : 3,
         "intcpt" : 8}

x_intersection, y_intersection = get_intersection(line1, line2)

message = [(1,2), (3,5),(x_intersection,y_intersection)]


for i in range(0,1):

    channel.basic_publish(exchange='race',
                          routing_key='lap',
                          body=json.dumps(message))

connection.close()