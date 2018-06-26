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
AMQP_PORT = 5672

# setting default race prams



total_number_of_laps  = 20

initial_race_start_time = 3  # <----- warm up time

slow_down_factor = 3  # <-- for debugging

lap_no = 1

rec_in_lap_count = 0

no_of_racer = sys.argv[1] if len(sys.argv) > 1 else "3"  # <---- define argparse option here

max_distance = 100  # <--- for debugging, original requirement = 10

racer_list = ["racer%d" % i for i in range(1, int(no_of_racer) + 1)]

farthest_racer = [racer_list[0], racer_list[1]]

farthest_racer_current_cordinates = [[0, 0], [0, 0]]

race_sent_message_log = {}

logging.basicConfig(format='%(asctime)s %(message)s')

logger = logging.getLogger()

logger.setLevel(logging.INFO)

logger.info("Master Sleeping")

logger.info("Hello From Master")


def generate_msg():
    """
    Generates a new race msg
    :return:
    """
    global lap_no, racer_list, race_sent_message_log

    logger.info(" settling every thing.. need 2 secs")  # <--- stablises it more logically (now for debug)
    sleep(3)

    logger.info(racer_list)

    # generate random origin point
    x = random.randint(1, 10)
    y = random.randint(1, 10)

    race_msg = [[]]
    for each_racer in racer_list:
        slope = random.randint(1, 10)
        intcpt = y - (slope * x)

        race_msg.append([slope, intcpt, x, y, lap_no])

    # increase lap number for next call
    lap_no = lap_no + 1  # <---- increase everytime message is generated
    logger.info("new next lap count --> {}".format(lap_no))
    logger.info(race_msg)

    return race_msg


def check_rabbitmq_server():
    """
    Wait till rabbit_mq server is up
    # TODO: need to make it more robust
    :return:
    """

    flag = False
    registerd_racer = 0
    while not flag:
        try:
            transport, protocol = yield from aioamqp.connect(AMQP_HOST, 5672)
            flag = True
            logger.info("RabbitMQ Server Up")
        except Exception:
            logger.info("RabbitMQ Server conection is closed")
            # delay to check
            sleep(1)

    for _ in range(0, initial_race_start_time):
        logger.info(" Looking for racers.....starting Race in {} sec....".format(initial_race_start_time - _))
        sleep(1)


async def time(websocket, path):
    while True:
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        print("sending logs from websocket")
        logging.info("sending logs from websocket")

        info = {
                "current_lap" : lap_no-1,
                "current_co_ordinates_of farthest": farthest_racer_current_cordinates
                }
        await websocket.send("---> " + json.dumps(info))
        await asyncio.sleep(3000)


start_server = websockets.serve(time, '0.0.0.0', 5678)

# test message
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


@asyncio.coroutine
def calculate_distance(channel):
    logger.info("calculating distance")

    logger.info(channel.queue)

    global farthest_racer_current_cordinates, race_sent_message_log, lap_no

    logger.info(farthest_racer)
    logger.info(farthest_racer_current_cordinates)

    x1 = farthest_racer_current_cordinates[0][0]
    y1 = farthest_racer_current_cordinates[0][1]
    x2 = farthest_racer_current_cordinates[1][0]
    y2 = farthest_racer_current_cordinates[1][1]

    dis = distance(x1, y1, x2, y2)

    logger.info("check_distnace %d" % dis)

    # send new lap message if not already sent and dis is greater than allowed
    if (dis > max_distance):

        # dis = 0
        farthest_racer_current_cordinates = [[0,0] , [0,0]]

        logger.info("Sending message for lap no  --> {}".format(lap_no))
        race_msg = generate_msg()

        race_sent_message_log[lap_no] = race_msg
        logger.info(race_msg)

        if lap_no < total_number_of_laps:

            logger.info("distance complete, sent new lap info ")
            yield from channel.publish(json.dumps(race_msg),
                                       exchange_name="race-exchange", routing_key="race")

        else:
            logger.info("Race is completed")
            yield from channel.publish("exit",
                                       exchange_name="race-exchange", routing_key="race")
            while True:
                choice  = input("Press L to see stats, anyother to quit")
                if choice == "Q" or choice =="q":
                    logger.info(race_sent_message_log)
                else:
                    logger.info(" *--* ")
                    exit()





    yield from asyncio.sleep(slow_down_factor)


@asyncio.coroutine
def exchange_routing_topic(msg):
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
    routing_key = 'race'

    yield from channel.exchange(exchange_name, 'topic')

    yield from channel.publish(msg, exchange_name=exchange_name, routing_key=routing_key)
    logger.info(" [x] Sent %r" % msg)

    yield from protocol.close()
    transport.close()


@asyncio.coroutine
def do_work(envelope, body, channel):
    global lap_no
    body = json.loads(body)
    logger.info(body)
    racer_name = body.get("racer_name")

    x = body.get("x")
    y = body.get("y")
    racer_lap_no = body.get("lap_no")
    logger.info("current master lap no ---> {}".format(lap_no))

    if (lap_no - 1) == racer_lap_no:

        if racer_name == farthest_racer[0]:
            farthest_racer_current_cordinates[0][0] = x
            farthest_racer_current_cordinates[0][1] = y

        if racer_name == farthest_racer[1]:
            farthest_racer_current_cordinates[1][0] = x
            farthest_racer_current_cordinates[1][1] = y

        # print(farthest_racer_current_cordinates)

        yield from calculate_distance(channel)

        logger.info('Racer --> {} , Point --> {},{} '.format(racer_name, x, y))
        print('Racer --> {} , Point --> {},{} '.format(racer_name, x, y))

    else:
        logger.info("message for pervious lap, current-lap is {} and msg lap is {}".format(lap_no - 1, racer_lap_no))

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



# start ws server
loop.run_until_complete(start_server)

# check rabbitmq server up or not
loop.run_until_complete(check_rabbitmq_server())

loop.create_task(manage_race())

loop.run_forever()
