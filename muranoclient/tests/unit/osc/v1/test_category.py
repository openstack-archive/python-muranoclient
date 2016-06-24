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

from muranoclient.osc.v1 import category as osc_category
from muranoclient.tests.unit.osc.v1 import fakes
from muranoclient.v1 import categories as api_category
from muranoclient.v1 import packages as api_packages

CATEGORY_INFO = {'id': 'xyz123',
                 'name': 'fake1',
                 'packages': [{'name': 'package1'}, {'name': 'package2'}]}


class TestCategory(fakes.TestApplicationCatalog):
    def setUp(self):
        super(TestCategory, self).setUp()
        self.category_mock = self.app.client_manager.application_catalog.\
            categories
        self.category_mock.reset_mock()
        self.packages_mock = \
            self.app.client_manager.application_catalog.packages


class TestListCategories(TestCategory):
    def setUp(self):
        super(TestListCategories, self).setUp()
        self.category_mock.list.return_value = [api_category.Category(None,
                                                CATEGORY_INFO)]

        # Command to test
        self.cmd = osc_category.ListCategories(self.app, None)

    @mock.patch('osc_lib.utils.get_item_properties')
    def test_category_list(self, mock_util):
        mock_util.return_value = ('xyz123', 'fake1')

        columns, data = self.cmd.take_action(parsed_args=None)

        # Check that columns are correct
        expected_columns = ['ID', 'Name']
        self.assertEqual(expected_columns, columns)

        # Check that data is correct
        expected_data = [('xyz123', 'fake1')]
        self.assertEqual(expected_data, data)


class TestShowCategory(TestCategory):
    def setUp(self):
        super(TestShowCategory, self).setUp()
        self.category_mock.get.return_value = api_category.\
            Category(None, CATEGORY_INFO)

        self.packages_mock.filter.return_value = [
            api_packages.Package(None, pkg_info) for pkg_info in CATEGORY_INFO[
                'packages']
        ]

        # Command to test
        self.cmd = osc_category.ShowCategory(self.app, None)

    @mock.patch('textwrap.wrap')
    def test_category_show(self, mock_wrap):
        arglist = ['xyz123']
        verifylist = [('id', 'xyz123')]

        mock_wrap.return_value = ['package1, package2']

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = self.cmd.take_action(parsed_args)

        # Check that columns are correct
        expected_columns = ('id', 'name', 'packages')
        self.assertEqual(expected_columns, columns)

        # Check that data is correct
        expected_data = ('xyz123', 'fake1', 'package1, package2')
        self.assertEqual(expected_data, data)


class TestCreateCategory(TestCategory):
    def setUp(self):
        super(TestCreateCategory, self).setUp()
        self.category_mock.add.return_value = [api_category.Category(None,
                                               CATEGORY_INFO)]

        # Command to test
        self.cmd = osc_category.CreateCategory(self.app, None)

    @mock.patch('osc_lib.utils.get_item_properties')
    def test_category_list(self, mock_util):
        arglist = ['fake1']
        verifylist = [('name', 'fake1')]

        mock_util.return_value = ('xyz123', 'fake1')

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = self.cmd.take_action(parsed_args)

        # Check that columns are correct
        expected_columns = ['ID', 'Name']
        self.assertEqual(expected_columns, columns)

        # Check that data is correct
        expected_data = [('xyz123', 'fake1')]
        self.assertEqual(expected_data, data)


class TestDeleteCategory(TestCategory):
    def setUp(self):
        super(TestDeleteCategory, self).setUp()
        self.category_mock.delete.return_value = None
        self.category_mock.list.return_value = [api_category.Category(None,
                                                CATEGORY_INFO)]

        # Command to test
        self.cmd = osc_category.DeleteCategory(self.app, None)

    @mock.patch('osc_lib.utils.get_item_properties')
    def test_category_list(self, mock_util):
        arglist = ['abc123', '123abc']
        verifylist = [('id', ['abc123', '123abc'])]

        mock_util.return_value = ('xyz123', 'fake1')

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = self.cmd.take_action(parsed_args)

        # Check that columns are correct
        expected_columns = ['ID', 'Name']
        self.assertEqual(expected_columns, columns)

        # Check that data is correct
        expected_data = [('xyz123', 'fake1')]
        self.assertEqual(expected_data, data)
