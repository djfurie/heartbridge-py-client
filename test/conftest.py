import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--url", action="store", default="http://localhost:8000", help="URL for the HeartBridge API Server"
    )


@pytest.fixture
def url(request):
    return request.config.getoption("--url")


@pytest.fixture
def wsurl(url):
    if url[0:4] == "http":
        return "ws" + url[4:]
