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

from muranoclient.osc.v1 import schema as osc_schema
from muranoclient.tests.unit.osc.v1 import fakes
from muranoclient.v1 import schemas as api_schemas

SAMPLE_CLASS_SCHEMA = {
    '': {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "properties": {}
    },
    'modelBuilder': {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "object",
        "properties": {}
    }
}


class TestSchema(fakes.TestApplicationCatalog):
    def setUp(self):
        super(TestSchema, self).setUp()
        self.schemas_mock = \
            self.app.client_manager.application_catalog.schemas
        self.schemas_mock.get.return_value = api_schemas.Schema(
            None, SAMPLE_CLASS_SCHEMA)
        self.cmd = osc_schema.ShowSchema(self.app, None)

    @mock.patch('osc_lib.utils.get_item_properties')
    def test_query_class_schema(self, mock_util):
        mock_util.return_value = 'result'

        arglist = ['class.name', 'methodName1',
                   '--package-name', 'package.name',
                   '--class-version', '>1']
        verifylist = [('class_name', 'class.name'),
                      ('method_names', ['methodName1']),
                      ('package_name', 'package.name'),
                      ('class_version', '>1')]

        parsed_args = self.check_parser(self.cmd, arglist, verifylist)

        columns, data = self.cmd.take_action(parsed_args)
        expected_columns = ['', 'modelBuilder']
        self.assertItemsEqual(expected_columns, columns)
        self.assertItemsEqual(tuple(SAMPLE_CLASS_SCHEMA.values()), data)
