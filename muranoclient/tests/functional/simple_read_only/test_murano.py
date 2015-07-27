# Copyright (c) 2015 Mirantis, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from muranoclient.tests.functional.simple_read_only import \
    murano_test_utils as utils


class SimpleReadOnlyMuranoClientTest(utils.CLIUtilsTestBase):
    """Basic, read-only tests for Murano CLI client.

    Basic smoke test for the Murano CLI commands which do not require
    creating or modifying murano objects.
    """

    def test_category_list(self):
        category = self.get_table_struct('category-list')
        self.assertEqual(category, ['ID', 'Name'])

    def test_env_template_list(self):
        templates = self.get_table_struct('env-template-list')
        self.assertEqual(templates, ['ID', 'Name', 'Created', 'Updated'])

    def test_environment_list(self):
        environment = self.get_table_struct('environment-list')
        self.assertEqual(environment, ['ID', 'Name', 'Created', 'Updated'])

    def test_package_list(self):
        packages = self.get_table_struct('package-list')
        self.assertEqual(packages, ['ID', 'Name', 'FQN',
                                    'Author', 'Is Public'])


class TableStructureMuranoClientTest(utils.CLIUtilsTestBase):
    """Smoke test for the Murano CLI commands which checks table
    structure after create or delete category, env-template
    environment and package.
    """

    def test_table_struct_deployment_list(self):
        """Test scenario:
            1) create environment
            2) check table structure
        """
        # Create environment
        env_name, environment, env_list = \
            self.create_murano_object('environment', 'MuranoTestTS-depl-list')

        env_id = self.get_value('ID', 'Name', env_name, environment)
        deployment = self.get_table_struct('deployment-list {0}'.
                                           format(env_id))
        self.assertEqual(deployment,
                         ['ID', 'State', 'Created', 'Updated', 'Finished'])

    def test_table_struct_of_environment_create(self):
        """Test scenario:
            1) create environment
            2) check table structure
        """
        # Create environment
        self.create_murano_object('environment', 'MuranoTestTS-env-create')

        environment = self.get_table_struct('environment-list')
        self.assertEqual(environment, ['ID', 'Name', 'Created', 'Updated'])

    def test_table_struct_of_environment_delete(self):
        """Test scenario:
            1) create environment
            2) delete environment
            3) check table structure
        """
        # Create environment
        env_name, environment, env_list = \
            self.create_murano_object('environment', 'MuranoTestTS-env-del')
        # Delete environment
        self.delete_murano_object('environment', env_name, environment)

        environment = self.get_table_struct('environment-list')
        self.assertEqual(environment, ['ID', 'Name', 'Created', 'Updated'])

    def test_table_struct_of_category_create(self):
        """Test scenario:
            1) create category
            2) check table structure
        """
        # Create category
        self.create_murano_object('category', 'MuranoTestTS-cat-create')

        category = self.get_table_struct('category-list')
        self.assertEqual(category, ['ID', 'Name'])

    def test_table_struct_of_category_delete(self):
        """Test scenario:
            1) create category
            2) delete category
            3) check table structure
        """
        # Create category
        cat_name, category, cat_list = \
            self.create_murano_object('category', 'MuranoTestTS-cat-create')

        self.delete_murano_object('category', cat_name, category)

        category = self.get_table_struct('category-list')
        self.assertEqual(category, ['ID', 'Name'])

    def test_table_struct_of_env_template_create(self):
        """Test scenario:
            1) create env_template
            2) check table structure
        """
        # Create env_template
        self.create_murano_object('env-template',
                                  'MuranoTestTS-env-tmp-create')

        env_template = self.get_table_struct('env-template-list')
        self.assertEqual(env_template, ['ID', 'Name', 'Created', 'Updated'])

    def test_table_struct_of_env_template_delete(self):
        """Test scenario:
            1) create env_template
            2) delete env_template
            3) check table structure
        """
        # Create env_template
        env_template_name, env_template, env_template_list = \
            self.create_murano_object('env-template',
                                      'MuranoTestTS-env-tmp-create')
        # Delete env_template
        self.delete_murano_object('env-template',
                                  env_template_name, env_template)

        env_template = self.get_table_struct('env-template-list')
        self.assertEqual(env_template, ['ID', 'Name', 'Created', 'Updated'])
