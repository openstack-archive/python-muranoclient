#    Copyright (c) 2013 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import unittest2 as unittest
import logging
from mock import MagicMock

from muranoclient.client import Client
import muranoclient.v1.environments as environments
import muranoclient.v1.services as services
import muranoclient.v1.sessions as sessions


def my_mock(*a, **b):
    return [a, b]


LOG = logging.getLogger('Unit tests')
api = MagicMock(json_request=my_mock)


class UnitTestsForClassesAndFunctions(unittest.TestCase):
    def test_create_client_instance(self):

        endpoint = 'http://no-resolved-host:8001'
        test_client = Client('1', endpoint=endpoint, token='1', timeout=10)

        assert test_client.environments is not None
        assert test_client.sessions is not None
        assert test_client.services is not None

    def test_env_manager_list(self):
        manager = environments.EnvironmentManager(api)
        result = manager.list()
        assert result == []

    def test_env_manager_create(self):
        manager = environments.EnvironmentManager(api)
        result = manager.create({'name': 'test'})
        assert result.body == {'name': 'test'}

    def test_env_manager_create_with_named_parameters(self):
        manager = environments.EnvironmentManager(api)
        result = manager.create(body={'name': 'test'})
        assert result.body == {'name': 'test'}

    def test_env_manager_create_negative_without_parameters(self):
        result = 'Exception'
        manager = environments.EnvironmentManager(api)
        try:
            result = manager.create()
        except TypeError:
            pass
        assert result is 'Exception'

    def test_env_manager_delete(self):
        manager = environments.EnvironmentManager(api)
        result = manager.delete('test')
        assert result is None

    def test_env_manager_delete_with_named_parameters(self):
        manager = environments.EnvironmentManager(api)
        result = manager.delete(environment_id='1')
        assert result is None

    def test_env_manager_delete_negative_without_parameters(self):
        result = 'Exception'
        manager = environments.EnvironmentManager(api)
        try:
            result = manager.delete()
        except TypeError:
            pass
        assert result is 'Exception'

    def test_env_manager_update(self):
        manager = environments.EnvironmentManager(api)
        result = manager.update('1', 'test')
        assert result.body == {'name': 'test'}

    def test_env_manager_update_with_named_parameters(self):
        manager = environments.EnvironmentManager(api)
        result = manager.update(environment_id='1',
                                name='test')
        assert result.body == {'name': 'test'}

    def test_env_manager_update_negative_with_one_parameter(self):
        result = 'Exception'
        manager = environments.EnvironmentManager(api)
        try:
            result = manager.update('test')
        except TypeError:
            pass
        assert result is 'Exception'

    def test_env_manager_update_negative_without_parameters(self):
        result = 'Exception'
        manager = environments.EnvironmentManager(api)
        try:
            result = manager.update()
        except TypeError:
            pass
        assert result is 'Exception'

    def test_env_manager_get(self):
        manager = environments.EnvironmentManager(api)
        result = manager.get('test')
        assert result.manager is not None

    def test_env(self):
        environment = environments.Environment(api, api)
        assert environment.data() is not None

    def test_session_manager_delete(self):
        manager = sessions.SessionManager(api)
        result = manager.delete('datacenter1', 'session1')
        assert result is None

    def test_session_manager_delete_with_named_parameters(self):
        manager = sessions.SessionManager(api)
        result = manager.delete(environment_id='datacenter1',
                                session_id='session1')
        assert result is None

    def test_session_manager_delete_negative_with_one_parameter(self):
        result = 'Exception'
        manager = sessions.SessionManager(api)
        try:
            result = manager.delete('datacenter1')
        except TypeError:
            pass
        assert result == 'Exception'

    def test_session_manager_delete_negative_without_parameters(self):
        result = 'Exception'
        manager = sessions.SessionManager(api)
        try:
            result = manager.delete()
        except TypeError:
            pass
        assert result == 'Exception'

    def test_session_manager_get(self):
        manager = sessions.SessionManager(api)
        result = manager.get('datacenter1', 'session1')
        # WTF?
        assert result.manager is not None

    def test_session_manager_configure(self):
        manager = sessions.SessionManager(api)
        result = manager.configure('datacenter1')
        assert result is not None

    def test_session_manager_configure_with_named_parameter(self):
        manager = sessions.SessionManager(api)
        result = manager.configure(environment_id='datacenter1')
        assert result is not None

    def test_session_manager_configure_negative_without_parameters(self):
        result = 'Exception'
        manager = sessions.SessionManager(api)
        try:
            result = manager.configure()
        except TypeError:
            pass
        assert result == 'Exception'

    def test_session_manager_deploy(self):
        manager = sessions.SessionManager(api)
        result = manager.deploy('datacenter1', '1')
        assert result is None

    def test_session_manager_deploy_with_named_parameters(self):
        manager = sessions.SessionManager(api)
        result = manager.deploy(environment_id='datacenter1',
                                session_id='1')
        assert result is None

    def test_session_manager_deploy_negative_with_one_parameter(self):
        result = 'Exception'
        manager = sessions.SessionManager(api)
        try:
            result = manager.deploy('datacenter1')
        except TypeError:
            pass
        assert result == 'Exception'

    def test_session_manager_deploy_negative_without_parameters(self):
        result = 'Exception'
        manager = sessions.SessionManager(api)
        try:
            result = manager.deploy()
        except TypeError:
            pass
        assert result == 'Exception'
