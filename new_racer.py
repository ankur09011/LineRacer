import asyncio
import aioamqp
import random
import json
import logging

import sys
from time import sleep


from helpers import solve_for_y





AMQP_HOST = "rabbit"
AMQP_PORT =  5672

logging.basicConfig(format='%(asctime)s %(message)s')

logger = logging.getLogger()

logger.setLevel(logging.INFO)

logger.info("Racer Sleeping")
logger.info("Hello From Racer")


#for debugging
slow_down_factor = 1

status = {'lap_no':1}

racer_number = int(sys.argv[1] if len(sys.argv) > 1 else "2")

racer_name = "racer{}".format(racer_number)


race_routing_key = "race"
print(racer_name)
logger.info(racer_name)



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
            logger.info("RabbitMQ server Up")
        except Exception:
            logger.info("RabbitMQ server conection is closed")
            sleep(0.05)

    channel = yield from protocol.channel()
    exchange_name = 'race-exchange'
    message = {"racer_name": racer_name}
    routing_key = 'register'

    yield from channel.exchange(exchange_name, 'topic')

    yield from channel.publish(json.dumps(message), exchange_name=exchange_name, routing_key=routing_key)
    logger.info("Registerd for racer as --> {}".format(racer_name))

    yield from protocol.close()
    transport.close()


@asyncio.coroutine
def exchange_routing_topic(x, y):
    try:
        transport, protocol = yield from aioamqp.connect(AMQP_HOST, 5672)
    except aioamqp.AmqpClosedConnection:
        print("closed connections")
        return

    channel = yield from protocol.channel()
    exchange_name = 'race-exchange'
    message = {"racer_name": racer_name, "x": x, "y": y, "lap_no": status.get("lap_no")}
    routing_key = 'master'

    yield from channel.exchange(exchange_name, 'topic')

    yield from channel.publish(json.dumps(message), exchange_name=exchange_name, routing_key=routing_key)
    logger.info(" [x] Sent {},{} ".format(x,y))

    yield from protocol.close()
    transport.close()


@asyncio.coroutine
def do_while_loop(body):

    global racer_number
    logger.info(body)
    logger.info("print starting lap")
    point = 0
    # asyncio.sleep(1)
    race = True
    body = json.loads(body)


    # debug --remove later

    logger.info(body)
    logger.info(type(body))


    lap_no = body[racer_number][4]
    x = body[racer_number][2]
    y = body[racer_number][3]
    slope = body[racer_number][0]
    intcpt = body[racer_number][1]


    line = {
            "slope":slope,
             "intcpt":intcpt
            }


    logger.info("x --> {}, y ----> {}".format(x,y))


    while race:

        global status

        x = x + 1
        y = solve_for_y(x, line)
        new_lap = status.get("lap_no")

        logger.info(new_lap)

        if not new_lap==lap_no:
            race = False

        sleep(slow_down_factor)

        yield from exchange_routing_topic(x,y)




def set_flag(lap_no):
    global status
    logger.info("setting flag for lap number --> {} ".format(lap_no))

    if not lap_no==status.get("lap_no"):
        status["lap_no"] = lap_no

@asyncio.coroutine
def do_work(envelope, body):


    logger.info("consumer {} recved {} ({})".format(envelope.consumer_tag, body, envelope.delivery_tag))

    msg = json.loads(body)


    logger.info(msg)
    logger.info(type(msg))

    lap_no = msg[racer_number][4]

    logger.info(" got lap no --> {} ".format(lap_no))
    set_flag(lap_no)

    # lap_no = json.loads(body).get("lap_no")

    yield from do_while_loop(body)

@asyncio.coroutine
def callback(channel, body, envelope, properties):
    loop = asyncio.get_event_loop()
    loop.create_task(do_work(envelope, body))

@asyncio.coroutine
def receive_log():
    try:
        transport, protocol = yield from aioamqp.connect(AMQP_HOST, 5672)
    except:
        print("closed connections")
        return

    channel = yield from protocol.channel()
    # exchange_name = 'cloudstack-events'
    exchange_name = 'race-exchange'
    queue_name = 'async-queue-%s' % random.randint(0, 10000)
    yield from channel.exchange(exchange_name, 'topic', auto_delete=False, passive=False, durable=False)
    yield from channel.basic_qos(prefetch_count=1, prefetch_size=0, connection_global=False)
    yield from asyncio.wait_for(channel.queue(queue_name, durable=False, auto_delete=True), timeout=10)

    binding_keys = [race_routing_key]

    for binding_key in binding_keys:
        print("binding", binding_key)
        yield from asyncio.wait_for(channel.queue_bind(exchange_name=exchange_name,
                                                       queue_name=queue_name,
                                                       routing_key=binding_key), timeout=10)

    logger.info(racer_name)
    logger.info(' waiting for command')
    logger.info(queue_name)
    yield from channel.basic_consume(callback, queue_name=queue_name)


loop = asyncio.get_event_loop()

loop.run_until_complete(check_rabbitmq_server())
loop.create_task(receive_log())
loop.run_forever()