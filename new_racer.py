import asyncio
import aioamqp
import random
import json


import sys
from time import sleep


from helpers import solve_for_y

status = {'lap_no':1}

racer_number = sys.argv[1] if len(sys.argv) > 1 else "2"
racer_name = "racer" + racer_number
race_routing_key = "race"
print(racer_name)

@asyncio.coroutine
def exchange_routing_topic(x, y):
    try:
        transport, protocol = yield from aioamqp.connect('localhost', 5672)
    except aioamqp.AmqpClosedConnection:
        print("closed connections")
        return

    channel = yield from protocol.channel()
    exchange_name = 'race-exchange'
    message = {"racer_name": racer_name, "x": x, "y": y}
    routing_key = sys.argv[1] if len(sys.argv) > 1 else 'master'

    yield from channel.exchange(exchange_name, 'topic')

    yield from channel.publish(json.dumps(message), exchange_name=exchange_name, routing_key=routing_key)
    print(" [x] Sent {},{} ".format(x,y))

    yield from protocol.close()
    transport.close()


@asyncio.coroutine
def do_while_loop(body):
    print(body)
    print("print starting race")
    point = 0
    # asyncio.sleep(1)
    race = True
    body = json.loads(body)
    lap_no = body.get("lap_no")
    x = body.get("x")
    y = body.get("y")

    line = {
            "slope":body.get(racer_name).get("slope"),
             "intcpt":body.get(racer_name).get("intcpt")
            }


    print(x, y)


    while race:

        global status

        x = x + 1
        y = solve_for_y(x, line)
        new_lap = status.get("lap_no")

        print(new_lap)

        if not new_lap==lap_no:
            race = False

        sleep(1)

        yield from exchange_routing_topic(x,y)


def set_flag(msg):
    global status
    print(json.loads(msg))
    msg = json.loads(msg)
    if not msg.get("lap_no")==status.get("lap_no"):
        status["lap_no"] = msg.get("lap_no")

@asyncio.coroutine
def do_work(envelope, body):
    print("consumer {} recved {} ({})".format(envelope.consumer_tag, body, envelope.delivery_tag))
    set_flag(body)
    lap_no = json.loads(body).get("lap_no")

    yield from do_while_loop(body)

@asyncio.coroutine
def callback(channel, body, envelope, properties):
    loop = asyncio.get_event_loop()
    loop.create_task(do_work(envelope, body))

@asyncio.coroutine
def receive_log():
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

    binding_keys = [race_routing_key]

    for binding_key in binding_keys:
        print("binding", binding_key)
        yield from asyncio.wait_for(channel.queue_bind(exchange_name=exchange_name,
                                                       queue_name=queue_name,
                                                       routing_key=binding_key), timeout=10)

    print(' [*] Waiting for logs. To exit press CTRL+C')
    print(queue_name)
    print(type(channel))
    yield from channel.basic_consume(callback, queue_name=queue_name)

loop = asyncio.get_event_loop()
loop.create_task(receive_log())
loop.run_forever()