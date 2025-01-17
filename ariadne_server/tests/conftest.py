"""configuration file for pytest"""
import os

os.environ['POSTGRES_DB'] = 'test'

from tests.fixtures.fake_context import context
from tests.fixtures.setup import schema, event_loop
from tests.fixtures.dummy_users import dummy_admin, dummy_user
