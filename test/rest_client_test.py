import pytest
import logging
import heartbridge
import jwt
import json
import random
import datetime
import asyncio

# Some Mock performance information to be used for token generation and checking
MOCK_ARTIST = "DJFury"
MOCK_TITLE = "Dougie's Furry Beats"
MOCK_EMAIL = "dougie.j.fleabottom@furiousenterprises.net"
MOCK_DESCRIPTION = "The furriest beats in music right meow"


@pytest.fixture()
async def client(url) -> heartbridge.RESTClient:
    logging.debug("Using %s for REST API", url)
    c = heartbridge.RESTClient(url)
    yield c
    await c.close()


@pytest.fixture()
async def token(client: heartbridge.RESTClient):
    logging.debug("Requesting new token")

    # Get a token for right now
    ret_val = await client.register(artist=MOCK_ARTIST,
                                    title=MOCK_TITLE,
                                    email=MOCK_EMAIL,
                                    description=MOCK_DESCRIPTION,
                                    duration=1)

    logging.debug("Returned payload: %s", ret_val)
    yield ret_val


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_date",
                         [datetime.datetime.now() - datetime.timedelta(minutes=6),
                          datetime.datetime.now() + datetime.timedelta(days=367)])
async def test_rest_register_bad_date(client, bad_date):
    ret = await client.register(artist=MOCK_ARTIST,
                                title=MOCK_TITLE,
                                performance_date=bad_date.timestamp(),
                                email=MOCK_EMAIL,
                                description=MOCK_DESCRIPTION,
                                duration=1)
    logging.debug(ret)
    assert "error" in json.dumps(ret)


@pytest.mark.asyncio
async def test_rest_register_bad_artist(client):
    ret = await client.register(artist="A" * 65,
                                title="B" * 65,
                                email=MOCK_EMAIL,
                                description=MOCK_DESCRIPTION,
                                duration=1,
                                performance_date=datetime.datetime.now().timestamp())
    logging.debug(ret)
    assert "error" in json.dumps(ret)


def test_rest_register(token):
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
    assert token_claims['email'] == MOCK_EMAIL
    assert token_claims['description'] == MOCK_DESCRIPTION


@pytest.mark.asyncio
async def test_rest_register_timestring(client: heartbridge.RESTClient):
    """ Register a performance using a date string """

    # utc_time_now = datetime.datetime.now(tz=datetime.timezone.utc)
    utc_time_now = datetime.datetime.utcnow()
    logging.error(utc_time_now.isoformat())

    token = await client.register(artist=MOCK_ARTIST, title=MOCK_TITLE,
                                  email=MOCK_EMAIL, description=MOCK_DESCRIPTION,
                                  duration=1,
                                  performance_date=utc_time_now.isoformat())

    # Performance Ids are expected to be 6 characters long
    performance_id = token['performance_id']
    assert len(performance_id) == 6

    # Decode the token
    token_claims = jwt.decode(token['token'], verify=False)
    logging.debug(token_claims)

    assert token_claims['artist'] == MOCK_ARTIST
    assert token_claims['title'] == MOCK_TITLE
    assert token_claims['email'] == MOCK_EMAIL
    assert token_claims['description'] == MOCK_DESCRIPTION
    assert datetime.datetime.utcfromtimestamp(
        token_claims['performance_date']) == utc_time_now.replace(microsecond=0)


@pytest.mark.asyncio
@pytest.mark.parametrize("field,new_value",
                         [('artist', 'DJFurioso'), ('title', 'A Fresh Title')])
async def test_rest_update(client, token, field, new_value):
    """ Register a performance, then update information """
    performance_id = token['performance_id']
    logging.info("PerformanceID: %s", performance_id)

    orig_token_claims = jwt.decode(token['token'], verify=False)
    logging.debug(orig_token_claims)

    # Update the field information
    ret_val = await client.update(token['token'], {field: new_value})

    # Make sure an error wasn't returned
    if "error" in ret_val:
        logging.debug(ret_val)
        assert False

    # Check to make sure the performance id has remained the same
    assert ret_val['performance_id'] == performance_id

    # Check to make sure the new artist information is in the new token
    new_token_claims = jwt.decode(ret_val['token'], verify=False)
    logging.debug(new_token_claims)
    assert new_token_claims[field] == new_value


@pytest.mark.asyncio
@pytest.mark.parametrize("field,new_value",
                         [('artist', 'DJFurioso' * 65), ('token', 'ABC123456890'),
                          ('performance_date', 0)])
async def test_rest_update_bad_values(client, token, field, new_value):
    """ Register a performance, then update information with bad values """
    performance_id = token['performance_id']
    logging.info("PerformanceID: %s", performance_id)

    orig_token_claims = jwt.decode(token['token'], verify=False)
    logging.debug(orig_token_claims)

    # Update the field information
    ret_val = await client.update(token['token'], {field: new_value})

    # Make sure an error was returned
    assert "error" in json.dumps(
        ret_val), "Oops, we expected to get an error returned here"


@pytest.mark.asyncio
async def test_rest_fetch_non_existent_performance_details(
        client: heartbridge.RESTClient):
    """ Have a client attempt to fetch a bogus performance id, expectation is it fails """
    ret_val = await client.get_event_details("AAAAAA")
    logging.debug(ret_val)
    assert "error" in json.dumps(
        ret_val), "Oops, we expected to get an error returned here"


@pytest.mark.asyncio
async def test_rest_fetch_performance_details(client: heartbridge.RESTClient, token):
    """ Register a performance, and then use the event detail endpoint to check if it's valid """
    performance_id = token["performance_id"]
    logging.info("PerformanceID: %s", performance_id)

    details = await client.get_event_details(performance_id)

    assert details['artist'] == MOCK_ARTIST
    assert details['title'] == MOCK_TITLE
    assert details['email'] == MOCK_EMAIL
    assert details['description'] == MOCK_DESCRIPTION


@pytest.mark.asyncio
async def test_rest_expire_performance(client: heartbridge.RESTClient, token):
    """ Register a performance and wait 1 minute to ensure it has expired """
    performance_id = token["performance_id"]
    logging.info("PerformanceID: %s", performance_id)

    details = await client.get_event_details(performance_id)

    assert details['artist'] == MOCK_ARTIST
    assert details['title'] == MOCK_TITLE
    assert details['email'] == MOCK_EMAIL
    assert details['description'] == MOCK_DESCRIPTION

    await asyncio.sleep(61)

    details = await client.get_event_details(performance_id)
    assert "error" in json.dumps(
        details), "Oops, we expected to get an error returned here"


@pytest.mark.asyncio
async def test_rest_fetch_performances(client: heartbridge.RESTClient, token):
    """ Register a new performance, then fetch the list of all performance and ensure it is in there """
    performance_id = token["performance_id"]
    logging.info("PerformanceID: %s", performance_id)

    ret_val = await client.get_events()

    # Loop through all of the returned events and pick out the one with our performance_id
    found = False
    for perf in ret_val["performances"]:
        if perf["performance_id"] == performance_id:
            found = True
            break

    assert found
    assert perf['artist'] == MOCK_ARTIST
    assert perf['title'] == MOCK_TITLE
    assert perf['email'] == MOCK_EMAIL
    assert perf['description'] == MOCK_DESCRIPTION
    assert perf['performance_id'] == performance_id


@pytest.mark.asyncio
async def test_rest_delete_performance(client: heartbridge.RESTClient, token):
    """" Register a new performance, then delete it """
    ret_val = await client.delete_performance(token["token"])

    assert ret_val["status"] == "success"


@pytest.mark.asyncio
async def test_rest_delete_performance_twice(client: heartbridge.RESTClient, token):
    """" Register a new performance, then delete it, twice... """
    ret_val = await client.delete_performance(token["token"])
    assert ret_val["status"] == "success"

    ret_val = await client.delete_performance(token["token"])
    assert "error" in json.dumps(
        ret_val), "Oops, we expected to get an error returned here"


@pytest.mark.asyncio
async def test_rest_delete_expired_performance(client: heartbridge.RESTClient, token):
    """" Register a new performance, wait for it to expire, then attempt to delete it """
    await asyncio.sleep(61)
    ret_val = await client.delete_performance(token["token"])
    assert "error" in json.dumps(
        ret_val), "Oops, we expected to get an error returned here"


@pytest.mark.asyncio
async def test_rest_delete_bogus_token(client: heartbridge.RESTClient):
    """" Attempt to delete a performance with an invalid token """
    ret_val = await client.delete_performance(
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    assert "error" in json.dumps(
        ret_val), "Oops, we expected to get an error returned here"


@pytest.mark.asyncio
async def test_rest_get_bogus_status(client: heartbridge.RESTClient):
    """ Attempt to get the status of a performance that hasn't been registered """
    ret_val = await client.get_event_status("AAAAAA")
    assert "error" in json.dumps(
        ret_val), "Oops, we expected to get an error returned here"


@pytest.mark.asyncio
async def test_rest_get_default_status(client: heartbridge.RESTClient, token):
    """ Register a performance and ensure default status is 'pending' """
    performance_id = token["performance_id"]
    ret_val = await client.get_event_status(performance_id)
    assert ret_val["status"] == 0


@pytest.mark.asyncio
async def test_rest_set_status(client: heartbridge.RESTClient, token):
    """ Register a performance, change the status and ensure read back of new  status """
    performance_id = token["performance_id"]
    ret_val = await client.get_event_status(performance_id)
    assert ret_val["status"] == 0

    await client.set_event_status(performance_id, token["token"], 2)
    ret_val = await client.get_event_status(performance_id)
    assert ret_val["status"] == 2


@pytest.mark.asyncio
async def test_rest_set_status_and_observe(client: heartbridge.RESTClient, token,
                                           wsurl):
    performance_id = token["performance_id"]

    wsclient = heartbridge.WSClient(wsurl)
    await wsclient.connect()
    await wsclient.subscribe(performance_id)

    # Keep taking in messages until a status update comes through
    while True:
        ret_val = await wsclient.wait_for_data()
        p = json.loads(ret_val)
        if p["action"] == "performance_status_update":
            break

    # Ensure that it is the expected default value
    assert p["status"] == 0

    # Update the performance status
    await client.set_event_status(performance_id, token["token"], 2)

    # Wait for the next status update message
    while True:
        ret_val = await wsclient.wait_for_data()
        p = json.loads(ret_val)
        if p["action"] == "performance_status_update":
            break

    assert p["status"] == 2

    await wsclient.close()
