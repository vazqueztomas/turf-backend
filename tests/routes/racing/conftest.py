import pytest
from polyfactory.factories.pydantic_factory import ModelFactory

from models.racing import Racing


class PersonFactory(ModelFactory[Racing]):
    __model__ = Racing


@pytest.fixture()
def racing() -> Racing:
    return PersonFactory.build()
