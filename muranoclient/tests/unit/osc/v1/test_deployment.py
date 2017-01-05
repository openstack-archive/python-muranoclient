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

from muranoclient.osc.v1 import deployment as osc_deployment
from muranoclient.tests.unit.osc.v1 import fakes
from muranoclient.v1 import deployments as api_deployment

DEPLOYMENT_COLUMNS = ('id', 'state', 'created', 'updated', 'finished')
DEPLOYMENT_DATA = ('xyz123', 'success', '2016-06-25T12:21:37',
                   '2016-06-25T12:21:47', '2016-06-25T12:21:47')
ALL_DEPLOYMENT_DATA = (('abc123', 'success', '2016-06-25T12:21:37',
                        '2016-06-25T12:21:47', '2016-06-25T12:21:47'),
                       ('xyz456', 'success', '2017-01-31T11:22:35',
                        '2017-01-31T11:22:47', '2017-01-31T11:22:47'))


class TestDeployment(fakes.TestApplicationCatalog):
    def setUp(self):
        super(TestDeployment, self).setUp()
        self.deployment_mock = self.app.client_manager.application_catalog.\
            deployments
        self.deployment_mock.reset_mock()
        self.environment_mock = self.app.client_manager.application_catalog.\
            environments


class TestListDeployment(TestDeployment):
    def setUp(self):
        super(TestListDeployment, self).setUp()
        deployment_info = dict(zip(DEPLOYMENT_COLUMNS, DEPLOYMENT_DATA))
        self.deployment_mock.list.return_value = \
            [api_deployment.Deployment(None, deployment_info)]

        # Command to test
        self.cmd = osc_deployment.ListDeployment(self.app, None)

    @mock.patch('osc_lib.utils.get_item_properties')
    def test_deployment_list(self, mock_util):
        arglist = ['xyz123']
        verifylist = [('id', 'xyz123')]
        mock_util.return_value = DEPLOYMENT_DATA

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = self.cmd.take_action(parsed_args)

        # Check that columns are correct
        expected_columns = [c.title() for c in DEPLOYMENT_COLUMNS]
        self.assertEqual(expected_columns, columns)

        # Check that data is correct
        expected_data = [DEPLOYMENT_DATA]
        self.assertEqual(expected_data, data)

    @mock.patch('osc_lib.utils.get_item_properties', autospec=True)
    def test_deployment_list_all_environments(self, mock_util):
        arglist = ['--all-environments']
        verifylist = [('id', None), ('all_environments', True)]
        mock_util.return_value = ALL_DEPLOYMENT_DATA

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = self.cmd.take_action(parsed_args)

        # Check that columns are correct
        expected_columns = [c.title() for c in DEPLOYMENT_COLUMNS]
        self.assertEqual(expected_columns, columns)

        # Check that data is correct
        expected_data = [ALL_DEPLOYMENT_DATA]
        self.assertEqual(expected_data, data)
