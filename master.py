import json
import aioamqp
import sys
from helpers import get_intersection, distance
import logging
from time import sleep
import time


from aiohttp import web

import asyncio
import datetime
import random
import websockets



AMQP_HOST = "rabbit"
AMQP_PORT =  5672



# setting default race prams
slow_down_factor = 3

lap_no = 2

rec_in_lap_count = 0

no_of_racer = 2

max_distance = 200

racer_list = ["racer%d" % i for i in range(1, no_of_racer + 1)]

farthest_racer = [racer_list[0], racer_list[1]]

farthest_racer_current_cordinates = [[0, 0], [0, 0]]

logging.basicConfig(format='%(asctime)s %(message)s')

logger = logging.getLogger()

logger.setLevel(logging.INFO)

logger.info("Master Sleeping")



logger.info("Hello From Master")



def check_rabbitmq_server():
    """
    Wait till rabbit_mq server is up
    # TODO: need to make it more robust
    :return:
    """

    flag = False

    while not flag:
        try:
            transport, protocol = yield from aioamqp.connect(AMQP_HOST, 5672)
            flag = True
            logger.info("Server Up")
        except Exception:
            logger.info("Server conection is closed")
            # delay to check
            sleep(1)

    for _ in range(0,10):
        logger.info("Starting Race in {} sec....".format(10-_))
        sleep(1)


async def time(websocket, path):
    while True:
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        print("sending logs from websocket")
        logging.info("sending logs from websocket")
        await websocket.send(str(now) + "---> from master")
        await asyncio.sleep(random.random() * 3)






start_server = websockets.serve(time, '0.0.0.0', 5678)


msg = {
    "x": 1,
    "y": 2,
    "lap_no": 1,
    "racer1": {"slope": 4,
               "intcpt": 3, },
    "racer2": {

        "slope": 4,
        "intcpt": 1, }

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

    sleep(slow_down_factor)


def generate_msg():
    global lap_no, racer_list

    race_msg = {"lap_no": lap_no}

    print(racer_list)

    x = random.randint(1, 10)
    y = random.randint(1, 10)

    race_msg["x"] = x
    race_msg["y"] = y

    for each_racer in racer_list:
        race_msg[each_racer] = {}
        slope = random.randint(1, 10)
        race_msg[each_racer]["slope"] = slope
        race_msg[each_racer]["intcpt"] = y - (slope * x)

    # increase lap number for next call
    lap_no = lap_no + 1

    return race_msg


@asyncio.coroutine
def exchange_routing_topic(msg):
    print("sending to racer1")
    try:
        transport, protocol = yield from aioamqp.connect(AMQP_HOST, 5672)
    except aioamqp.AmqpClosedConnection:
        logging.exception("Error connecting AMQP")
        return
    except Exception as e:
        logging.exception("Error connecting AMQP")
        return
    channel = yield from protocol.channel()
    print(sys.argv)
    exchange_name = 'race-exchange'
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

    # print(farthest_racer_current_cordinates)
    calculate_distance(channel)
    logger.info('Racer --> {} , Point --> {},{} '.format(racer_name, x, y))
    print('Racer --> {} , Point --> {},{} '.format(racer_name, x, y))

    yield


@asyncio.coroutine
def callback(channel, body, envelope, properties):
    loop = asyncio.get_event_loop()
    loop.create_task(do_work(envelope, body, channel))


@asyncio.coroutine
def manage_race():
    try:
        transport, protocol = yield from aioamqp.connect(AMQP_HOST, 5672)
    except:
        logger.info("closed connections")
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

    logging.info("sending start signal, will sleep for 1 second")
    # yield from asyncio.wait_for(exchange_routing_topic(),1)
    race_msg = generate_msg()
    yield from channel.publish(json.dumps(race_msg), exchange_name=exchange_name, routing_key="race")
    logging.info(" [x] Sent %r" % race_msg)

    logger.info(' waiting for command')


    yield from channel.basic_consume(callback, queue_name=queue_name)



loop = asyncio.get_event_loop()

loop.run_until_complete(start_server)
loop.run_until_complete(check_rabbitmq_server())
loop.create_task(manage_race())
loop.run_forever()