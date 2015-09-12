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

import mock
import testtools

from muranoclient import client
from muranoclient.v1 import actions
import muranoclient.v1.environments as environments
from muranoclient.v1 import packages
import muranoclient.v1.sessions as sessions
import muranoclient.v1.templates as templates


def my_mock(*a, **b):
    return [a, b]


api = mock.MagicMock(json_request=my_mock)


class UnitTestsForClassesAndFunctions(testtools.TestCase):
    def test_create_client_instance(self):

        endpoint = 'http://no-resolved-host:8001'
        test_client = client.Client('1', endpoint=endpoint,
                                    token='1', timeout=10)

        self.assertIsNotNone(test_client.environments)
        self.assertIsNotNone(test_client.sessions)
        self.assertIsNotNone(test_client.services)

    def test_env_manager_list(self):
        manager = environments.EnvironmentManager(api)
        result = manager.list()

        self.assertEqual([], result)

    def test_env_manager_create(self):
        manager = environments.EnvironmentManager(api)
        result = manager.create({'name': 'test'})

        self.assertEqual({'name': 'test'}, result.data)

    def test_env_manager_create_with_named_parameters(self):
        manager = environments.EnvironmentManager(api)
        result = manager.create(data={'name': 'test'})

        self.assertEqual({'name': 'test'}, result.data)

    def test_env_manager_create_negative_without_parameters(self):

        manager = environments.EnvironmentManager(api)

        self.assertRaises(TypeError, manager.create)

    def test_env_manager_delete(self):
        manager = environments.EnvironmentManager(api)
        result = manager.delete('test')

        self.assertIsNone(result)

    def test_env_manager_delete_with_named_parameters(self):
        manager = environments.EnvironmentManager(api)
        result = manager.delete(environment_id='1')

        self.assertIsNone(result)

    def test_env_manager_delete_negative_without_parameters(self):

        manager = environments.EnvironmentManager(api)

        self.assertRaises(TypeError, manager.delete)

    def test_env_manager_update(self):
        manager = environments.EnvironmentManager(api)
        result = manager.update('1', 'test')

        self.assertEqual({'name': 'test'}, result.data)

    def test_env_manager_update_with_named_parameters(self):
        manager = environments.EnvironmentManager(api)
        result = manager.update(environment_id='1',
                                name='test')

        self.assertEqual({'name': 'test'}, result.data)

    def test_env_manager_update_negative_with_one_parameter(self):

        manager = environments.EnvironmentManager(api)

        self.assertRaises(TypeError, manager.update, 'test')

    def test_env_manager_update_negative_without_parameters(self):

        manager = environments.EnvironmentManager(api)

        self.assertRaises(TypeError, manager.update)

    def test_env_manager_get(self):
        manager = environments.EnvironmentManager(api)
        result = manager.get('test')

        self.assertIsNotNone(result.manager)

    def test_env(self):
        environment = environments.Environment(api, api)

        self.assertIsNotNone(environment.data())

    def test_session_manager_delete(self):
        manager = sessions.SessionManager(api)
        result = manager.delete('datacenter1', 'session1')

        self.assertIsNone(result)

    def test_session_manager_delete_with_named_parameters(self):
        manager = sessions.SessionManager(api)
        result = manager.delete(environment_id='datacenter1',
                                session_id='session1')

        self.assertIsNone(result)

    def test_session_manager_delete_negative_with_one_parameter(self):

        manager = sessions.SessionManager(api)

        self.assertRaises(TypeError, manager.delete, 'datacenter1')

    def test_session_manager_delete_negative_without_parameters(self):

        manager = sessions.SessionManager(api)

        self.assertRaises(TypeError, manager.delete)

    def test_session_manager_get(self):
        manager = sessions.SessionManager(api)
        result = manager.get('datacenter1', 'session1')
        # WTF?
        self.assertIsNotNone(result.manager)

    def test_session_manager_configure(self):
        manager = sessions.SessionManager(api)
        result = manager.configure('datacenter1')

        self.assertIsNotNone(result)

    def test_session_manager_configure_with_named_parameter(self):
        manager = sessions.SessionManager(api)
        result = manager.configure(environment_id='datacenter1')

        self.assertIsNotNone(result)

    def test_session_manager_configure_negative_without_parameters(self):

        manager = sessions.SessionManager(api)

        self.assertRaises(TypeError, manager.configure)

    def test_session_manager_deploy(self):
        manager = sessions.SessionManager(api)
        result = manager.deploy('datacenter1', '1')

        self.assertIsNone(result)

    def test_session_manager_deploy_with_named_parameters(self):
        manager = sessions.SessionManager(api)
        result = manager.deploy(environment_id='datacenter1',
                                session_id='1')

        self.assertIsNone(result)

    def test_session_manager_deploy_negative_with_one_parameter(self):

        manager = sessions.SessionManager(api)

        self.assertRaises(TypeError, manager.deploy, 'datacenter1')

    def test_session_manager_deploy_negative_without_parameters(self):

        manager = sessions.SessionManager(api)

        self.assertRaises(TypeError, manager.deploy)

    def test_action_manager_call(self):
        api_mock = mock.MagicMock(
            json_request=lambda *args, **kwargs: (None, {'task_id': '1234'}))
        manager = actions.ActionManager(api_mock)
        result = manager.call('testEnvId', 'testActionId', ['arg1', 'arg2'])
        self.assertEqual('1234', result)

    def test_package_filter_pagination_next_marker(self):
        """``PackageManager.filter`` handles `next_marker` parameter related
        to pagination in API correctly.
        """
        responses = [
            {'next_marker': 'test_marker',
             'packages': [{'name': 'test_package_1'}]},
            {'packages': [{'name': 'test_package_2'}]}
        ]

        def json_request(method, url, *args, **kwargs):
            self.assertIn('/v1/catalog/packages', url)

            return mock.MagicMock(), responses.pop(0)

        api = mock.MagicMock()
        api.configure_mock(**{'json_request.side_effect': json_request})

        manager = packages.PackageManager(api)
        list(manager.filter())

        self.assertEqual(2, api.json_request.call_count)

    def test_package_filter_encoding_good(self):
        responses = [
            {'next_marker': 'test_marker',
             'packages': [{'name': 'test_package_1'}]},
            {'packages': [{'name': 'test_package_2'}]}
        ]

        def json_request(method, url, *args, **kwargs):
            self.assertIn('category=%D0%BF%D0%B8%D0%B2%D0%BE', url)
            return mock.MagicMock(), responses.pop(0)

        api = mock.MagicMock()
        api.configure_mock(**{'json_request.side_effect': json_request})

        manager = packages.PackageManager(api)
        category = '\xd0\xbf\xd0\xb8\xd0\xb2\xd0\xbe'
        kwargs = {'category': category.decode('utf-8')}
        list(manager.filter(**kwargs))

        self.assertEqual(2, api.json_request.call_count)

    def test_action_manager_get_result(self):
        api_mock = mock.MagicMock(
            json_request=lambda *args, **kwargs: (None, {'a': 'b'}))
        manager = actions.ActionManager(api_mock)
        result = manager.get_result('testEnvId', '1234')
        self.assertEqual({'a': 'b'}, result)

    def test_env_template_manager_list(self):
        """It tests the list of environment templates.
        """
        manager = templates.EnvTemplateManager(api)
        result = manager.list()

        self.assertEqual([], result)

    def test_env_template_manager_create(self):
        manager = templates.EnvTemplateManager(api)
        result = manager.create({'name': 'test'})

        self.assertEqual({'name': 'test'}, result.data)

    def test_env_template_manager_create_with_named_parameters(self):
        manager = templates.EnvTemplateManager(api)
        result = manager.create(data={'name': 'test'})

        self.assertEqual({'name': 'test'}, result.data)

    def test_env_template_manager_create_negative_without_parameters(self):
        manager = templates.EnvTemplateManager(api)
        self.assertRaises(TypeError, manager.create)

    def test_env_template_manager_delete(self):
        manager = templates.EnvTemplateManager(api)
        result = manager.delete('test')

        self.assertIsNone(result)

    def test_env_template_manager_delete_with_named_parameters(self):
        manager = templates.EnvTemplateManager(api)
        result = manager.delete(env_template_id='1')

        self.assertIsNone(result)

    def test_env_template_manager_delete_negative_without_parameters(self):

        manager = templates.EnvTemplateManager(api)

        self.assertRaises(TypeError, manager.delete)

    def test_env_template_manager_update(self):
        manager = templates.EnvTemplateManager(api)
        result = manager.update('1', 'test')

        self.assertEqual({'name': 'test'}, result.data)

    def test_env_template_manager_update_with_named_parameters(self):
        manager = templates.EnvTemplateManager(api)
        result = manager.update(env_template_id='1',
                                name='test')

        self.assertEqual({'name': 'test'}, result.data)

    def test_env_template_manager_update_negative_with_one_parameter(self):

        manager = templates.EnvTemplateManager(api)

        self.assertRaises(TypeError, manager.update, 'test')

    def test_env_template_manager_update_negative_without_parameters(self):

        manager = templates.EnvTemplateManager(api)

        self.assertRaises(TypeError, manager.update)

    def test_env_template_manager_get(self):
        manager = templates.EnvTemplateManager(api)
        result = manager.get('test')

        self.assertIsNotNone(result.manager)
