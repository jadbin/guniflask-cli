import pytest
from guniflask.test import app_test_client


@pytest.fixture
def client():
    with app_test_client() as client:
        client.application.config['TESTING'] = True
        yield client
