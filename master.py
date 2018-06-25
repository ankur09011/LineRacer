import json
import pika
import asyncio
import aioamqp
import random
import sys

import time
import random
from helpers import get_intersection, distance


# from helpers import get_intersection
#
#
# connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
#
# channel = connection.channel()
#
# channel.exchange_declare(exchange='race',
#                          exchange_type='direct')
#
#
# line1 = {"slope" : 5.5,
#          "intcpt" : 2}
#
# line2 = {"slope" : 3,
#          "intcpt" : 8}
#
# x_intersection, y_intersection = get_intersection(line1, line2)
#
# message = [(1,2), (3,5),(x_intersection,y_intersection)]
#
#
# for i in range(0,1):
#
#     channel.basic_publish(exchange='race',
#                           routing_key='lap',
#                           body=json.dumps(message))
#
# connection.close()



lap_no = 2

rec_in_lap_count = 0

no_of_racer = 2

max_distance = 50000

racer_list = ["racer%d"%i for i in range(1,no_of_racer+1)]

farthest_racer = [racer_list[0],racer_list[1]]

farthest_racer_current_cordinates = [[0,0],[0,0]]





msg = {
            "x" : 1,
            "y": 2,
"lap_no":1,
            "racer1": {"slope": 4,
             "intcpt": 3,},
"racer2": {"slope": 4,
             "intcpt": 1,}

        }


def calculate_distance(channel):

    print("check_distnace")

    global farthest_racer_current_cordinates

    x1 = farthest_racer_current_cordinates[0][0]
    y1 = farthest_racer_current_cordinates[0][1]
    x2 = farthest_racer_current_cordinates[1][0]
    y2 = farthest_racer_current_cordinates[1][1]

    dis = distance(x1, y1, x2, y2)

    print("check_distnace %d" % dis)

    if dis > max_distance:
        race_msg = generate_msg()

        channel.publish(json.dumps(race_msg), exchange_name="race-exchange", routing_key="race")
        print(" [x] Sent %r" % race_msg)

    time.sleep(3)

def generate_msg():
    global lap_no, racer_list

    race_msg = {"lap_no":lap_no}

    print(racer_list)

    x = random.randint(1,10)
    y = random.randint(1,10)

    race_msg["x"] = x
    race_msg["y"] = y


    for each_racer in racer_list:
        race_msg[each_racer] = {}
        slope = random.randint(1,10)
        race_msg[each_racer]["slope"] = slope
        race_msg[each_racer] ["intcpt"] = y - ( slope * x)

    # increase lap number for next call
    lap_no = lap_no + 1

    return race_msg




@asyncio.coroutine
def exchange_routing_topic(msg):



    print("sending to racer1")
    try:
        transport, protocol = yield from aioamqp.connect('localhost', 5672)
    except aioamqp.AmqpClosedConnection:
        print("closed connections")
        return

    channel = yield from protocol.channel()
    print(sys.argv)
    exchange_name = 'race-exchange'
    message = ' '.join(sys.argv[2:]) or 'I am racer1, I got something'
    routing_key = sys.argv[1] if len(sys.argv) > 1 else 'race'

    yield from channel.exchange(exchange_name, 'topic')



    yield from channel.publish(msg, exchange_name=exchange_name, routing_key=routing_key)
    print(" [x] Sent %r" % msg)

    yield from protocol.close()
    transport.close()


@asyncio.coroutine
def do_work(envelope, body, channel):
    body = json.loads(body)
    racer_name = body.get("racer_name")
    x = body.get("x")
    y = body.get("y")

    if racer_name == farthest_racer[0]:
        farthest_racer_current_cordinates[0][0] = x
        farthest_racer_current_cordinates[0][1] = y

    if racer_name == farthest_racer[1]:
        farthest_racer_current_cordinates[1][0] = x
        farthest_racer_current_cordinates[1][1] = y

    calculate_distance(channel)

    print('Racer --> {} , Point --> {},{} '.format(racer_name,x,y))
    yield

@asyncio.coroutine
def callback(channel, body, envelope, properties):
    loop = asyncio.get_event_loop()
    loop.create_task(do_work(envelope, body, channel))

@asyncio.coroutine
def manage_race():
    try:
        transport, protocol = yield from aioamqp.connect('localhost', 5672)
    except:
        print("closed connections")
        return

    channel = yield from protocol.channel()
    # exchange_name = 'cloudstack-events'
    exchange_name = 'race-exchange'
    queue_name = 'async-queue-%s' % random.randint(0, 10000)
    yield from channel.exchange(exchange_name, 'topic', auto_delete=False, passive=False, durable=False)
    yield from asyncio.wait_for(channel.queue(queue_name, durable=False, auto_delete=True), timeout=10)

    binding_keys = ['master']

    for binding_key in binding_keys:
        print("binding", binding_key)
        yield from asyncio.wait_for(channel.queue_bind(exchange_name=exchange_name,
                                                       queue_name=queue_name,
                                                       routing_key=binding_key), timeout=10)

    print(queue_name)
    print(type(channel))

    print("sending start signal, will sleep for 1 second")
    # yield from asyncio.wait_for(exchange_routing_topic(),1)
    race_msg = generate_msg()
    yield from channel.publish(json.dumps(race_msg), exchange_name=exchange_name, routing_key="race")
    print(" [x] Sent %r" % race_msg)

    print(' [*] Waiting for logs. To exit press CTRL+C')

    yield from channel.basic_consume(callback, queue_name=queue_name)

loop = asyncio.get_event_loop()
# loop.create_task(exchange_routing_topic())
loop.create_task(manage_race())
loop.run_forever()