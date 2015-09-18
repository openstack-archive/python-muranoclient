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
        self.assertEqual(['ID', 'Name'], category)

    def test_env_template_list(self):
        templates = self.get_table_struct('env-template-list')
        self.assertEqual(['ID', 'Name', 'Created', 'Updated'], templates)

    def test_environment_list(self):
        environment = self.get_table_struct('environment-list')
        self.assertEqual(['ID', 'Name', 'Created', 'Updated'], environment)

    def test_package_list(self):
        packages = self.get_table_struct('package-list')
        self.assertEqual(['ID', 'Name', 'FQN', 'Author', 'Is Public'],
                         packages)


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
        environment = self.create_murano_object('environment',
                                                'MuranoTestTS-depl-list')
        table_struct = self.get_table_struct('deployment-list',
                                             params=environment['ID'])
        self.assertEqual(['ID', 'State', 'Created', 'Updated', 'Finished'],
                         table_struct)

    def test_table_struct_of_environment_create(self):
        """Test scenario:
            1) create environment
            2) check table structure
        """
        self.create_murano_object('environment', 'MuranoTestTS-env-create')
        table_struct = self.get_table_struct('environment-list')
        self.assertEqual(['ID', 'Name', 'Created', 'Updated'], table_struct)

    def test_table_struct_of_environment_delete(self):
        """Test scenario:
            1) create environment
            2) delete environment
            3) check table structure
        """
        environment = self.create_murano_object('environment',
                                                'MuranoTestTS-env-del')
        self.delete_murano_object('environment', environment)
        table_struct = self.get_table_struct('environment-list')
        self.assertEqual(['ID', 'Name', 'Created', 'Updated'], table_struct)

    def test_table_struct_of_category_create(self):
        """Test scenario:
            1) create category
            2) check table structure
        """
        self.create_murano_object('category', 'MuranoTestTS-cat-create')
        table_struct = self.get_table_struct('category-list')
        self.assertEqual(['ID', 'Name'], table_struct)

    def test_table_struct_of_category_delete(self):
        """Test scenario:
            1) create category
            2) delete category
            3) check table structure
        """
        category = self.create_murano_object('category',
                                             'MuranoTestTS-cat-create')
        self.delete_murano_object('category', category)
        category = self.get_table_struct('category-list')
        self.assertEqual(['ID', 'Name'], category)

    def test_table_struct_of_env_template_create(self):
        """Test scenario:
            1) create env_template
            2) check table structure
        """
        self.create_murano_object('env-template',
                                  'MuranoTestTS-env-tmp-create')
        table_struct = self.get_table_struct('env-template-list')
        self.assertEqual(['ID', 'Name', 'Created', 'Updated'], table_struct)

    def test_table_struct_of_env_template_delete(self):
        """Test scenario:
            1) create env_template
            2) delete env_template
            3) check table structure
        """
        env_template = self.create_murano_object('env-template',
                                                 'MuranoTestTS-env-tmp-create')
        self.delete_murano_object('env-template', env_template)
        table_struct = self.get_table_struct('env-template-list')
        self.assertEqual(['ID', 'Name', 'Created', 'Updated'], table_struct)


class EnvironmentMuranoSanityClientTest(utils.CLIUtilsTestBase):
    """Sanity tests for testing actions with environment.

    Smoke test for the Murano CLI commands which checks basic actions with
    environment command like create, delete, rename etc.
    """

    def test_environment_create(self):
        """Test scenario:
            1) create environment
            2) check that created environment exist
        """
        environment = self.create_murano_object('environment',
                                                'TestMuranoSanityEnv')
        env_list = self.listing('environment-list')

        self.assertIn(environment, env_list)

    def test_environment_delete(self):
        """Test scenario:
            1) create environment
            2) delete environment
        """
        environment = self.create_murano_object('environment',
                                                'TestMuranoSanityEnv')
        self.delete_murano_object('environment', environment)
        env_list = self.listing('environment-list')

        self.assertNotIn(environment, env_list)

    def test_environment_rename(self):
        """Test scenario:
            1) create environment
            2) rename environment
        """
        environment = self.create_murano_object('environment',
                                                'TestMuranoSanityEnv')

        new_env_name = self.generate_name('TestMuranoSEnv-env-rename')
        rename_params = "{0} {1}".format(environment['Name'], new_env_name)
        new_list = self.listing('environment-rename', params=rename_params)
        renamed_env = self.get_object(new_list, new_env_name)
        self.addCleanup(self.delete_murano_object, 'environment', renamed_env)
        new_env_list = self.listing('environment-list')

        self.assertIn(renamed_env, new_env_list)
        self.assertNotIn(environment, new_env_list)

    def test_table_struct_env_show(self):
        """Test scenario:
            1) create environment
            2) check structure of env_show object
        """
        environment = self.create_murano_object('environment',
                                                'TestMuranoSanityEnv')
        env_show = self.listing('environment-show', params=environment['Name'])
        # Check structure of env_show object
        self.assertEqual(['created', 'id', 'name', 'services', 'status',
                          'tenant_id', 'updated', 'version'],
                         map(lambda x: x['Property'], env_show))

    def test_environment_show(self):
        """Test scenario:
            1) create environment
            2) check that env_name, ID, updated and created values
               exist in env_show object
        """
        environment = self.create_murano_object('environment',
                                                'TestMuranoSanityEnv')
        env_show = self.listing('environment-show', params=environment['Name'])

        self.assertIn(environment['Created'],
                      map(lambda x: x['Value'], env_show))
        self.assertIn(environment['Updated'],
                      map(lambda x: x['Value'], env_show))
        self.assertIn(environment['Name'], map(lambda x: x['Value'], env_show))
        self.assertIn(environment['ID'], map(lambda x: x['Value'], env_show))
