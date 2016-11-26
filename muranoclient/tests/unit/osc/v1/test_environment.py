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

import collections
import json
import tempfile

import mock

from muranoclient.osc.v1 import environment as osc_env
from muranoclient.tests.unit.osc.v1 import fakes
from muranoclient.v1 import environments as api_env

ENV_INFO = {'id': '1234',
            'name': 'Fake Environment',
            'created': '2015-12-16T17:31:54',
            'updated': '2015-12-16T17:31:54',
            'networking': {},
            'services': ['fake services'],
            'status': 'fake deployed',
            'tenant_id': 'xyz123',
            'version': '1'}

ENV_MODEL = {
    "defaultNetworks": {
        "environment": {
            "name": "env-network",
            "?": {
                "type": "io.murano.resources.NeutronNetwork",
                "id": "5678"
            }
        },
        "flat": None
    },
    "region": "RegionOne",
    "name": "env",
    "?": {
        "updated": "2016-10-03 09:33:41.039789",
        "type": "io.murano.Environment",
        "id": "1234"
    }
}


class TestEnvironment(fakes.TestApplicationCatalog):
    def setUp(self):
        super(TestEnvironment, self).setUp()
        self.environment_mock = self.app.client_manager.application_catalog.\
            environments
        self.session_mock = self.app.client_manager.application_catalog.\
            sessions
        self.services_mock = self.app.client_manager.application_catalog.\
            services
        self.environment_mock.reset_mock()


class TestListEnvironment(TestEnvironment):
    def setUp(self):
        super(TestListEnvironment, self).setUp()
        self.environment_mock.list.return_value = [api_env.Environment(None,
                                                   ENV_INFO)]

        # Command to test
        self.cmd = osc_env.ListEnvironments(self.app, None)

    @mock.patch('osc_lib.utils.get_item_properties')
    def test_environment_list_with_no_options(self, mock_util):
        arglist = []
        verifylist = []

        mock_util.return_value = ('1234', 'Environment of all tenants',
                                  'fake deployed', '2015-12-16T17:31:54',
                                  '2015-12-16T17:31:54'
                                  )

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = self.cmd.take_action(parsed_args)

        # Check that columns are correct
        expected_columns = ['Id', 'Name', 'Status', 'Created', 'Updated']
        self.assertEqual(expected_columns, columns)

        # Check that data is correct
        expected_data = [('1234', 'Environment of all tenants',
                          'fake deployed', '2015-12-16T17:31:54',
                          '2015-12-16T17:31:54')]
        self.assertEqual(expected_data, data)

    @mock.patch('osc_lib.utils.get_item_properties')
    def test_environment_list_with_all_tenants(self, mock_util):
        arglist = ['--all-tenants']
        verifylist = [('all_tenants', True), ('tenant', None)]

        mock_util.return_value = ('1234', 'Environment of all tenants',
                                  'fake deployed', '2015-12-16T17:31:54',
                                  '2015-12-16T17:31:54'
                                  )

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = self.cmd.take_action(parsed_args)

        # Check that columns are correct
        expected_columns = ['Id', 'Name', 'Status', 'Created', 'Updated']
        self.assertEqual(expected_columns, columns)

        # Check that data is correct
        expected_data = [('1234', 'Environment of all tenants',
                          'fake deployed', '2015-12-16T17:31:54',
                          '2015-12-16T17:31:54')]
        self.assertEqual(expected_data, data)
        self.environment_mock.list.assert_called_once_with(True, None)

    @mock.patch('osc_lib.utils.get_item_properties')
    def test_environment_list_with_tenant(self, mock_util):
        arglist = ['--tenant=ABC']
        verifylist = [('all_tenants', False), ('tenant', 'ABC')]

        mock_util.return_value = ('1234', 'Environment of tenant ABC',
                                  'fake deployed', '2015-12-16T17:31:54',
                                  '2015-12-16T17:31:54'
                                  )

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = self.cmd.take_action(parsed_args)

        # Check that columns are correct
        expected_columns = ['Id', 'Name', 'Status', 'Created', 'Updated']
        self.assertEqual(expected_columns, columns)

        # Check that data is correct
        expected_data = [('1234', 'Environment of tenant ABC',
                          'fake deployed', '2015-12-16T17:31:54',
                          '2015-12-16T17:31:54')]
        self.assertEqual(expected_data, data)
        self.environment_mock.list.assert_called_once_with(False, 'ABC')


class TestShowEnvironment(TestEnvironment):
    def setUp(self):
        super(TestShowEnvironment, self).setUp()
        mock_to_dict = self.environment_mock.get.return_value.to_dict
        mock_to_dict.return_value = ENV_INFO

        self.cmd = osc_env.ShowEnvironment(self.app, None)

    @mock.patch('oslo_serialization.jsonutils.dumps')
    def test_environment_show_with_no_options(self, mock_json):
        arglist = ['fake']
        verifylist = [('id', 'fake')]

        mock_json.return_value = ['fake services']

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = self.cmd.take_action(parsed_args)

        # Check that columns are correct
        expected_columns = ('created', 'id', 'name', 'networking', 'services',
                            'status', 'tenant_id', 'updated', 'version')
        self.assertEqual(expected_columns, columns)

        # Check that data is correct
        expected_data = ('2015-12-16T17:31:54', '1234', 'Fake Environment',
                         {}, ['fake services'], 'fake deployed', 'xyz123',
                         '2015-12-16T17:31:54', '1')
        self.assertEqual(expected_data, data)

    @mock.patch('oslo_serialization.jsonutils.dumps')
    def test_environment_show_with_only_app_option(self, mock_json):
        arglist = ['fake', '--only-apps']
        verifylist = [('id', 'fake'), ('only_apps', True)]

        mock_json.return_value = ['fake services']

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = self.cmd.take_action(parsed_args)

        # Check that columns are correct
        expected_columns = ['services']
        self.assertEqual(expected_columns, columns)

        # Check that data is correct
        expected_data = [['fake services']]
        self.assertEqual(expected_data, data)

    @mock.patch('oslo_serialization.jsonutils.dumps')
    def test_environment_show_with_session_id_option(self, mock_json):
        arglist = ['fake', '--session-id', 'abc123']
        verifylist = [('id', 'fake'), ('session_id', 'abc123')]

        mock_json.return_value = ['fake services']

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = self.cmd.take_action(parsed_args)

        # Check that columns are correct
        expected_columns = ('created', 'id', 'name', 'networking', 'services',
                            'status', 'tenant_id', 'updated', 'version')
        self.assertEqual(expected_columns, columns)

        # Check that data is correct
        expected_data = ('2015-12-16T17:31:54', '1234', 'Fake Environment',
                         {}, ['fake services'], 'fake deployed', 'xyz123',
                         '2015-12-16T17:31:54', '1')
        self.assertEqual(expected_data, data)


class TestRenameEnvironment(TestEnvironment):
    def setUp(self):
        super(TestRenameEnvironment, self).setUp()
        self.environment_mock.update.return_value = [api_env.Environment(None,
                                                     ENV_INFO)]

        # Command to test
        self.cmd = osc_env.RenameEnvironment(self.app, None)

    @mock.patch('osc_lib.utils.get_item_properties')
    def test_environment_rename(self, mock_util):
        arglist = ['1234', 'fake-1']
        verifylist = [('id', '1234'), ('name', 'fake-1')]

        mock_util.return_value = ('1234', 'fake-1', 'fake deployed',
                                  '2015-12-16T17:31:54', '2015-12-16T17:31:54'
                                  )

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = self.cmd.take_action(parsed_args)

        # Check that columns are correct
        expected_columns = ['Id', 'Name', 'Status', 'Created', 'Updated']
        self.assertEqual(expected_columns, columns)

        # Check that data is correct
        expected_data = [('1234', 'fake-1', 'fake deployed',
                          '2015-12-16T17:31:54', '2015-12-16T17:31:54')]
        self.assertEqual(expected_data, data)


class TestEnvironmentSessionCreate(TestEnvironment):
    def setUp(self):
        super(TestEnvironmentSessionCreate, self).setUp()

        # Command to test
        self.cmd = osc_env.EnvironmentSessionCreate(self.app, None)

    @mock.patch('muranoclient.common.utils.text_wrap_formatter')
    def test_environment_session_create(self, mock_util):
        arglist = ['1234']
        verifylist = [('id', '1234')]

        mock_util.return_value = '1abc2xyz'

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = self.cmd.take_action(parsed_args)

        # Check that columns are correct
        expected_columns = ['id']
        self.assertEqual(expected_columns, columns)

        # Check that data is correct
        expected_data = ['1abc2xyz']
        self.assertEqual(expected_data, data)


class TestEnvironmentCreate(TestEnvironment):
    def setUp(self):
        super(TestEnvironmentCreate, self).setUp()
        self.environment_mock.create.return_value = [api_env.Environment(None,
                                                     ENV_INFO)]

        # Command to test
        self.cmd = osc_env.EnvironmentCreate(self.app, None)

    @mock.patch('osc_lib.utils.get_item_properties')
    def test_environment_create_with_no_option(self, mock_util):
        arglist = ['fake']
        verifylist = [('name', 'fake')]

        mock_util.return_value = ('1234', 'fake', 'ready',
                                  '2015-12-16T17:31:54', '2015-12-16T17:31:54')

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = self.cmd.take_action(parsed_args)

        # Check that columns are correct
        expected_columns = ['Id', 'Name', 'Status', 'Created', 'Updated']
        self.assertEqual(expected_columns, columns)

        # Check that data is correct
        expected_data = [('1234', 'fake', 'ready',
                          '2015-12-16T17:31:54', '2015-12-16T17:31:54')]
        self.assertEqual(expected_data, data)

    @mock.patch('osc_lib.utils.get_item_properties')
    def test_environment_create_with_region_option(self, mock_util):
        arglist = ['fake', '--region', 'region_one']
        verifylist = [('name', 'fake'), ('region', 'region_one')]

        mock_util.return_value = ('1234', 'fake', 'ready',
                                  '2015-12-16T17:31:54', '2015-12-16T17:31:54')

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = self.cmd.take_action(parsed_args)

        # Check that correct arguments are passed
        self.environment_mock.create.assert_has_calls([mock.call(
            {'name': 'fake', 'region': 'region_one'})])

        # Check that columns are correct
        expected_columns = ['Id', 'Name', 'Status', 'Created', 'Updated']
        self.assertEqual(expected_columns, columns)

        # Check that data is correct
        expected_data = [('1234', 'fake', 'ready',
                          '2015-12-16T17:31:54', '2015-12-16T17:31:54')]
        self.assertEqual(expected_data, data)

    @mock.patch('osc_lib.utils.get_item_properties')
    def test_environment_create_with_net_option(self, mock_util):
        arglist = ['fake', '--join-net-id', 'x1y2z3']
        verifylist = [('name', 'fake'), ('join_net_id', 'x1y2z3')]

        mock_util.return_value = ('1234', 'fake', 'ready',
                                  '2015-12-16T17:31:54', '2015-12-16T17:31:54')

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = self.cmd.take_action(parsed_args)

        expected_call = {
            'defaultNetworks': {
                'environment': {
                    'internalNetworkName': 'x1y2z3',
                    '?': {
                        'type': 'io.murano.resources.ExistingNeutronNetwork',
                        'id': mock.ANY
                    }
                },
                'flat': None
            },
            'name': 'fake',
            'region': None
        }

        # Check that correct arguments are passed
        self.environment_mock.create.assert_called_with(expected_call)

        # Check that columns are correct
        expected_columns = ['Id', 'Name', 'Status', 'Created', 'Updated']
        self.assertEqual(expected_columns, columns)

        # Check that data is correct
        expected_data = [('1234', 'fake', 'ready',
                          '2015-12-16T17:31:54', '2015-12-16T17:31:54')]
        self.assertEqual(expected_data, data)

    @mock.patch('osc_lib.utils.get_item_properties')
    def test_environment_create_with_subnet_option(self, mock_util):
        arglist = ['fake', '--join-subnet-id', 'x1y2z3']
        verifylist = [('name', 'fake'), ('join_subnet_id', 'x1y2z3')]

        mock_util.return_value = ('1234', 'fake', 'ready',
                                  '2015-12-16T17:31:54', '2015-12-16T17:31:54')

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = self.cmd.take_action(parsed_args)

        expected_call = {
            'defaultNetworks': {
                'environment': {
                    'internalSubnetworkName': 'x1y2z3',
                    '?': {
                        'type': 'io.murano.resources.ExistingNeutronNetwork',
                        'id': mock.ANY
                    }
                },
                'flat': None
            },
            'name': 'fake',
            'region': None
        }

        # Check that correct arguments are passed
        self.environment_mock.create.assert_called_with(expected_call)

        # Check that columns are correct
        expected_columns = ['Id', 'Name', 'Status', 'Created', 'Updated']
        self.assertEqual(expected_columns, columns)

        # Check that data is correct
        expected_data = [('1234', 'fake', 'ready',
                          '2015-12-16T17:31:54', '2015-12-16T17:31:54')]
        self.assertEqual(expected_data, data)


class TestEnvironmentDelete(TestEnvironment):
    def setUp(self):
        super(TestEnvironmentDelete, self).setUp()
        self.environment_mock.delete.return_value = None
        self.environment_mock.list.return_value = [api_env.Environment(None,
                                                   ENV_INFO)]

        # Command to test
        self.cmd = osc_env.EnvironmentDelete(self.app, None)

    @mock.patch('osc_lib.utils.get_item_properties')
    def test_environment_delete(self, mock_util):
        arglist = ['fake1', 'fake2']
        verifylist = [('id', ['fake1', 'fake2'])]

        mock_util.return_value = ('1234', 'Environment of all tenants',
                                  'fake deployed', '2015-12-16T17:31:54',
                                  '2015-12-16T17:31:54'
                                  )

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = self.cmd.take_action(parsed_args)

        # Check that columns are correct
        expected_columns = ['Id', 'Name', 'Status', 'Created', 'Updated']
        self.assertEqual(expected_columns, columns)

        # Check that data is correct
        expected_data = [('1234', 'Environment of all tenants',
                          'fake deployed', '2015-12-16T17:31:54',
                          '2015-12-16T17:31:54')]
        self.assertEqual(expected_data, data)


class TestEnvironmentDeploy(TestEnvironment):
    def setUp(self):
        super(TestEnvironmentDeploy, self).setUp()
        mock_to_dict = self.environment_mock.get.return_value.to_dict
        mock_to_dict.return_value = ENV_INFO

        # Command to test
        self.cmd = osc_env.EnvironmentDeploy(self.app, None)

    @mock.patch('oslo_serialization.jsonutils.dumps')
    def test_environment_deploy(self, mock_json):
        arglist = ['fake', '--session-id', 'abc123']
        verifylist = [('id', 'fake'), ('session_id', 'abc123')]

        mock_json.return_value = ['fake services']

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = self.cmd.take_action(parsed_args)

        # Check that columns are correct
        expected_columns = ('created', 'id', 'name', 'networking', 'services',
                            'status', 'tenant_id', 'updated', 'version')
        self.assertEqual(expected_columns, columns)

        # Check that data is correct
        expected_data = ('2015-12-16T17:31:54', '1234', 'Fake Environment',
                         {}, ['fake services'], 'fake deployed', 'xyz123',
                         '2015-12-16T17:31:54', '1')
        self.assertEqual(expected_data, data)


class TestEnvironmentAppsEdit(TestEnvironment):
    def setUp(self):
        super(TestEnvironmentAppsEdit, self).setUp()

        # Command to test
        self.cmd = osc_env.EnvironmentAppsEdit(self.app, None)

    def test_environment_apps_edit(self):
        fake = collections.namedtuple('fakeEnv', 'services')
        self.environment_mock.get.side_effect = [
            fake(services=[
                {'?': {'name': "foo"}}
            ]),
        ]

        temp_file = tempfile.NamedTemporaryFile(prefix="murano-test", mode='w')
        json.dump([
            {'op': 'replace', 'path': '/0/?/name',
                'value': "dummy"
             }
        ], temp_file)
        temp_file.file.flush()

        arglist = ['fake', '--session-id', 'abc123', temp_file.name]

        parsed_args = self.check_parser(self.cmd, arglist, [])

        self.cmd.take_action(parsed_args)

        self.services_mock.put.assert_called_once_with(
            'fake',
            session_id='abc123',
            path='/',
            data=[{'?': {'name': 'dummy'}}]
        )


class TestEnvironmentModelShow(TestEnvironment):
    def setUp(self):
        super(TestEnvironmentModelShow, self).setUp()
        self.env_mock = \
            self.app.client_manager.application_catalog.environments
        self.env_mock.get_model.return_value = ENV_MODEL

        # Command to test
        self.cmd = osc_env.EnvironmentModelShow(self.app, None)

    def test_environment_model_show_basic(self):
        arglist = ['env-id']
        verifylist = [('id', 'env-id')]
        parsed_args = self.check_parser(self.cmd, arglist, verifylist)
        columns, data = self.cmd.take_action(parsed_args)

        # Check that columns are correct
        expected_columns = ('?', 'defaultNetworks', 'name', 'region')
        self.assertEqual(expected_columns, columns)

        # Check that data is correct
        self.assertItemsEqual(ENV_MODEL.values(), data)

    def test_environment_model_show_full(self):
        arglist = ['env-id', '--path', '/path', '--session-id', 'sess-id']
        verifylist = [('id', 'env-id'), ('path', '/path'),
                      ('session_id', 'sess-id')]
        parsed_args = self.check_parser(self.cmd, arglist, verifylist)
        columns, data = self.cmd.take_action(parsed_args)

        # Check that columns are correct
        expected_columns = ('?', 'defaultNetworks', 'name', 'region')
        self.assertEqual(expected_columns, columns)

        # Check that data is correct
        self.assertItemsEqual(ENV_MODEL.values(), data)


class TestEnvironmentModelEdit(TestEnvironment):
    def setUp(self):
        super(TestEnvironmentModelEdit, self).setUp()
        self.env_mock = \
            self.app.client_manager.application_catalog.environments
        self.env_mock.update_model.return_value = ENV_MODEL

        # Command to test
        self.cmd = osc_env.EnvironmentModelEdit(self.app, None)

    def test_environment_model_edit(self):
        temp_file = tempfile.NamedTemporaryFile(prefix="murano-test", mode='w')
        patch = [{'op': 'replace', 'path': '/name', 'value': 'dummy'}]
        json.dump(patch, temp_file)
        temp_file.file.flush()

        arglist = ['env-id', temp_file.name, '--session-id', 'sess-id']
        verifylist = [('id', 'env-id'), ('filename', temp_file.name),
                      ('session_id', 'sess-id')]
        parsed_args = self.check_parser(self.cmd, arglist, verifylist)
        columns, data = self.cmd.take_action(parsed_args)

        # Check that columns are correct
        expected_columns = ('?', 'defaultNetworks', 'name', 'region')
        self.assertEqual(expected_columns, columns)

        # Check that data is correct
        self.assertItemsEqual(ENV_MODEL.values(), data)
