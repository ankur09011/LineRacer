import json
import pika

from helpers import solve_for_y

connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
channel = connection.channel()


channel.exchange_declare(exchange='race',
                         exchange_type='direct')

result = channel.queue_declare(exclusive=False)

queue_name = result.method.queue

message_type = ['lap']

for each in message_type:
    print(each)
    channel.queue_bind(exchange='race',
                       queue=queue_name,
                       routing_key=each)


def callback(ch, method, properties, body):

    message = json.loads(body)

    line = {
            "slope": message[0][0],
            "intcpt": message[0][1],
            "x_intersection": message[-1][0],
            "y_intersection": message[-1][1]
            }

    print(line)
    x = line.get("x_intersection")

    x = x + 1
    y = solve_for_y(x, line)

    print(x,y)


channel.basic_consume(callback,
                      queue=queue_name,
                      no_ack=True)

channel.start_consuming()