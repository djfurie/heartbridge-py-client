import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--url", action="store", default="ws://localhost:8000", help="WebSocket URL for the HeartBridge API Server"
    )


@pytest.fixture
def url(request):
    return request.config.getoption("--url")
