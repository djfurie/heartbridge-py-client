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
async def client(url):
    logging.debug("Using %s for REST API", url)
    c = heartbridge.RESTClient(url)
    yield c
    await c.close()


@pytest.fixture()
async def token(client):
    logging.debug("Requesting new token")

    # Get a token for right now
    ret_val = await client.register(artist=MOCK_ARTIST,
                                    title=MOCK_TITLE,
                                    email=MOCK_EMAIL,
                                    description=MOCK_DESCRIPTION,
                                    duration=90)

    logging.debug("Returned payload: %s", ret_val)
    yield ret_val


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_date", [datetime.datetime.now() - datetime.timedelta(minutes=6),
                                      datetime.datetime.now() + datetime.timedelta(days=367)])
async def test_rest_register_bad_date(client, bad_date):
    ret = await client.register(artist=MOCK_ARTIST,
                                title=MOCK_TITLE,
                                performance_date=bad_date.timestamp(),
                                email=MOCK_EMAIL,
                                description=MOCK_DESCRIPTION,
                                duration=90)
    logging.debug(ret)
    assert "error" in json.dumps(ret)


@pytest.mark.asyncio
async def test_rest_register_bad_artist(client):
    ret = await client.register(artist="A" * 65,
                                title="B" * 65,
                                email=MOCK_EMAIL,
                                description=MOCK_DESCRIPTION,
                                duration=90,
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
@pytest.mark.parametrize("field,new_value", [('artist', 'DJFurioso'), ('title', 'A Fresh Title')])
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
                         [('artist', 'DJFurioso' * 65), ('token', 'ABC123456890'), ('performance_date', 0)])
async def test_rest_update_bad_values(client, token, field, new_value):
    """ Register a performance, then update information with bad values """
    performance_id = token['performance_id']
    logging.info("PerformanceID: %s", performance_id)

    orig_token_claims = jwt.decode(token['token'], verify=False)
    logging.debug(orig_token_claims)

    # Update the field information
    ret_val = await client.update(token['token'], {field: new_value})

    # Make sure an error was returned
    assert "error" in json.dumps(ret_val), "Oops, we expected to get an error returned here"
