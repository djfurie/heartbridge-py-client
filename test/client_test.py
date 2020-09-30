import pytest
import logging
import heartbridge
import time
import jwt
import json
import random
import concurrent.futures
import datetime
import asyncio

# Some Mock performance information to be used for token generation and checking
MOCK_ARTIST = "DJFury"
MOCK_TITLE = "Dougie's Furry Beats"


class Publisher:
    def __init__(self, client, token):
        self.client = client
        self.token = token['token']
        self.performance_id = token['performance_id']
        self._interval = 1.0
        self._running = False
        self.total_events_published = 0
        self._run_task = None

    async def _thread_func(self):
        logging.debug("Publisher thread running")
        while self._running:
            logging.debug("Publisher thread publishing")
            heart_rate = random.randint(60, 180)
            await self.client.publish(self.token, heart_rate)
            self.total_events_published += 1
            await asyncio.sleep(self._interval)

    async def start(self, interval: float = 1.0):
        logging.debug("Publisher thread start")
        self._interval = interval
        self._running = True
        self._run_task = asyncio.create_task(self._thread_func())

    async def stop(self):
        logging.debug("Publisher thread stop")
        self._running = False
        self._run_task.cancel()
        try:
            await self._run_task
        except asyncio.exceptions.CancelledError:
            pass


@pytest.fixture()
def publisher(client, token):
    yield Publisher(client, token)


@pytest.fixture()
async def client(url):
    logging.debug("Connecting to %s", url)
    c = heartbridge.Client(url)
    await c.connect()
    yield c
    logging.debug("Closing connection")
    await c.close()


@pytest.fixture()
async def token(client):
    logging.debug("Requesting new token")

    # Get a token for right now
    ret_val = await client.register(artist=MOCK_ARTIST,
                                    title=MOCK_TITLE)

    logging.debug("Returned payload: %s", ret_val)
    p = json.loads(ret_val)
    yield p


@pytest.mark.asyncio
async def test_connect(client):
    assert client.is_connected
    logging.info("Connection established... closing connection")
    await client.close()
    assert not client.is_connected
    logging.info("Connection closed")


@pytest.mark.asyncio
async def test_invalid_action(client):
    await client._ws.send(json.dumps({'action': 'bad-action'}))
    ret = await client.wait_for_data()
    logging.debug(ret)

    assert "error" in json.loads(ret)


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_date", [datetime.datetime.now() - datetime.timedelta(minutes=6),
                                      datetime.datetime.now() + datetime.timedelta(days=367)])
async def test_register_bad_date(client, bad_date):
    ret = await client.register(artist=MOCK_ARTIST,
                                title=MOCK_TITLE,
                                performance_date=bad_date.timestamp())
    logging.debug(ret)
    assert "error" in json.dumps(ret)


@pytest.mark.asyncio
async def test_register_bad_artist(client):
    ret = await client.register(artist="A" * 65,
                                title="B" * 65,
                                performance_date=datetime.datetime.now().timestamp())
    logging.debug(ret)
    assert "error" in json.dumps(ret)


def test_register(token):
    """ Register a performance - make sure that a token is returned """

    # Extract the Performance Id that was provided
    performance_id = token['performance_id']
    logging.info("PerformanceID: %s", performance_id)

    # Performance Ids are expected to be 6 characters long
    assert len(performance_id) == 6

    # Decode the token
    token_claims = jwt.decode(token['token'], verify=False)
    logging.debug(token_claims)

    assert token_claims['artist'] == MOCK_ARTIST
    assert token_claims['title'] == MOCK_TITLE


@pytest.mark.asyncio
@pytest.mark.parametrize("field,new_value", [('artist', 'DJFurioso'), ('title', 'A Fresh Title')])
async def test_update(client, token, field, new_value):
    """ Register a performance, then update information """
    performance_id = token['performance_id']
    logging.info("PerformanceID: %s", performance_id)

    orig_token_claims = jwt.decode(token['token'], verify=False)
    logging.debug(orig_token_claims)

    # Update the field information
    ret_val = await client.update(token['token'], {field: new_value})
    p = json.loads(ret_val)

    # Make sure an error wasn't returned
    if "error" in p:
        logging.debug(p)
        assert False

    # Check to make sure the performance id has remained the same
    assert p['performance_id'] == performance_id

    # Check to make sure the new artist information is in the new token
    new_token_claims = jwt.decode(p['token'], verify=False)
    logging.debug(new_token_claims)
    assert new_token_claims[field] == new_value


@pytest.mark.asyncio
@pytest.mark.parametrize("field,new_value",
                         [('artist', 'DJFurioso' * 65), ('token', 'ABC123456890'), ('performance_date', 0)])
async def test_update_bad_values(client, token, field, new_value):
    """ Register a performance, then update information with bad values """
    performance_id = token['performance_id']
    logging.info("PerformanceID: %s", performance_id)

    orig_token_claims = jwt.decode(token['token'], verify=False)
    logging.debug(orig_token_claims)

    # Update the field information
    ret_val = await client.update(token['token'], {field: new_value})
    p = json.loads(ret_val)

    # Make sure an error was returned
    assert "error" in p, "Oops, we expected to get an error returned here"


@pytest.mark.asyncio
async def test_publish(publisher: Publisher):
    """ Test publishing heartrate """

    await publisher.start(interval=0.1)
    await asyncio.sleep(5)
    await publisher.stop()


@pytest.mark.asyncio
@pytest.mark.parametrize('num_subscriptions', [1, 2, 10, 100])
async def test_subscribe(publisher: Publisher, url, num_subscriptions):
    """
    This test is pretty bad right now.  There are all sorts of timing things that may break it
    It's a generally decent way to test basic functions in the server, but much better testing
    should be devised if we really need to stress test and reliability test this thing
    """

    # This is the main loop for subscribers.  This will need to run in a thread per subscriber
    # because there is no timeout mechanism for wait_for_data.
    async def client_loop(tclient: heartbridge.Client):
        num_rx = 0
        while True:
            logging.debug("Client: %s", tclient.connection_id)
            try:
                ret = await tclient.wait_for_data()
                logging.debug(ret)
                p = json.loads(ret)
                if 'heartrate' in p:
                    logging.debug("Client: %s -- Got heart rate update: %s", client.connection_id, ret)
                    num_rx += 1
                if 'active_subcriptions' in p:
                    logging.debug("Client: %s -- Active Subcriptions: %s", client.connection_id, ret)
            except Exception:
                # Capture any exception and use that to return here.  The expectation is that we will
                # get a socket closed exception when the main test body closes all of the connections down
                return num_rx

    # Set up all of the subscribers...
    clients = []
    for i in range(num_subscriptions):
        # Create the client
        logging.debug("Connecting to: %s", url)
        client = heartbridge.Client(url)
        await client.connect()

        # Subscribe to a performance
        await client.subscribe(publisher.performance_id)

        # Submit the client run loop to the thread pool
        t = asyncio.create_task(client_loop(client))

        # Store it
        clients.append((client, t))

    # Start the publisher
    await publisher.start(interval=1)

    # After a certain number of events, have the publisher stop
    while True:
        await asyncio.sleep(0.1)
        if publisher.total_events_published == 10:
            break

    await publisher.stop()

    # Shutdown each subscriber connection (which will terminate their thread) and gather up the results
    total_num_rx = 0
    for iclient, t in clients:
        await iclient.close()
        result = await t
        total_num_rx += result

    assert total_num_rx == publisher.total_events_published * num_subscriptions
