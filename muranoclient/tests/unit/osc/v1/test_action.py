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

from unittest import mock

from muranoclient.osc.v1 import action as osc_action
from muranoclient.tests.unit.osc.v1 import fakes
from muranoclient.v1 import static_actions as api_static_actions


class TestAction(fakes.TestApplicationCatalog):
    def setUp(self):
        super(TestAction, self).setUp()
        self.static_actions_mock = \
            self.app.client_manager.application_catalog.static_actions


class TestStaticActionCall(TestAction):
    def setUp(self):
        super(TestStaticActionCall, self).setUp()
        self.static_actions_mock.call.return_value = \
            api_static_actions.StaticActionResult('result')

        # Command to test
        self.cmd = osc_action.StaticActionCall(self.app, None)

    @mock.patch('osc_lib.utils.get_item_properties')
    def test_static_action_call_basic(self, mock_util):
        mock_util.return_value = 'result'

        arglist = ['class.name', 'method.name']
        verifylist = [('class_name', 'class.name'),
                      ('method_name', 'method.name')]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = self.cmd.take_action(parsed_args)

        # Check that columns are correct
        expected_columns = ['Static action result']
        self.assertEqual(expected_columns, columns)

        # Check that data is correct
        expected_data = ['result']
        self.assertEqual(expected_data, data)

    @mock.patch('osc_lib.utils.get_item_properties')
    def test_static_action_call_full(self, mock_util):
        mock_util.return_value = 'result'

        arglist = ['class.name', 'method.name',
                   '--arguments', 'food=spam', 'parrot=dead',
                   '--package-name', 'package.name',
                   '--class-version', '>1']
        verifylist = [('class_name', 'class.name'),
                      ('method_name', 'method.name'),
                      ('arguments', ['food=spam', 'parrot=dead']),
                      ('package_name', 'package.name'),
                      ('class_version', '>1')]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = self.cmd.take_action(parsed_args)

        # Check that columns are correct
        expected_columns = ['Static action result']
        self.assertEqual(expected_columns, columns)

        # Check that data is correct
        expected_data = ['result']
        self.assertEqual(expected_data, data)
