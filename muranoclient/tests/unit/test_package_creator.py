#    Copyright (c) 2014 Mirantis, Inc.
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

import os
import shutil

from muranoclient.openstack.common.apiclient import exceptions
from muranoclient.tests.unit import base
from muranoclient.v1.package_creator import hot_package
from muranoclient.v1.package_creator import mpl_package


FIXTURE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                           'fixture_data'))
TEMPLATE = os.path.join(FIXTURE_DIR, 'heat-template.yaml')
CLASSES_DIR = os.path.join(FIXTURE_DIR, 'test-app', 'Classes')
RESOURCES_DIR = os.path.join(FIXTURE_DIR, 'test-app', 'Resources')
UI = os.path.join(FIXTURE_DIR, 'test-app', 'ui.yaml')
LOGO = os.path.join(FIXTURE_DIR, 'logo.png')


class TestArgs(object):
    pass


class PackageCreatorTest(base.TestAdditionalAsserts):

    def test_generate_hot_manifest(self):
        args = TestArgs()
        args.template = TEMPLATE
        args.name = 'test_name'
        args.author = 'TestAuthor'
        args.full_name = None
        args.tags = None
        args.description = None
        expected_manifest = {
            'Format': 'Heat.HOT/1.0',
            'Type': 'Application',
            'FullName': 'io.murano.apps.generated.TestName',
            'Name': 'test_name',
            'Description': 'Heat-defined application '
                           'for a template "heat-template.yaml"',
            'Author': 'TestAuthor',
            'Tags': ['Heat-generated']
        }
        result_manifest = hot_package.generate_manifest(args)
        self.check_dict_is_subset(expected_manifest, result_manifest)

    def test_generate_hot_manifest_nonexistent_template(self):
        args = TestArgs()
        args.template = '/home/this/path/does/not/exist'
        self.assertRaises(exceptions.CommandError,
                          hot_package.generate_manifest,
                          args)

    def test_generate_hot_manifest_with_all_parameters(self):
        args = TestArgs()
        args.template = TEMPLATE
        args.name = 'test_name'
        args.author = 'TestAuthor'
        args.full_name = 'test.full.name.TestName'
        args.tags = ['test', 'tag', 'Heat']
        args.description = 'Test description'

        expected_manifest = {
            'Format': 'Heat.HOT/1.0',
            'Type': 'Application',
            'FullName': 'test.full.name.TestName',
            'Name': 'test_name',
            'Description': 'Test description',
            'Author': 'TestAuthor',
            'Tags': ['test', 'tag', 'Heat']
        }
        result_manifest = hot_package.generate_manifest(args)
        self.check_dict_is_subset(expected_manifest, result_manifest)

    def test_generate_hot_manifest_template_not_yaml(self):
        args = TestArgs()
        args.template = LOGO
        args.name = None
        args.full_name = None
        self.assertRaises(exceptions.CommandError,
                          hot_package.generate_manifest, args)

    def test_prepare_hot_package(self):
        args = TestArgs()
        args.template = TEMPLATE
        args.name = 'test_name'
        args.author = 'TestAuthor'
        args.full_name = 'test.full.name.TestName'
        args.tags = 'test, tag, Heat'
        args.description = 'Test description'
        args.resources_dir = RESOURCES_DIR
        args.logo = LOGO
        package_dir = hot_package.prepare_package(args)

        prepared_files = ['manifest.yaml', 'logo.png',
                          'template.yaml', 'Resources']
        self.assertEqual(sorted(prepared_files),
                         sorted(os.listdir(package_dir)))
        shutil.rmtree(package_dir)

    def test_generate_mpl_manifest(self):
        args = TestArgs()
        args.template = TEMPLATE
        args.classes_dir = CLASSES_DIR
        args.resources_dir = RESOURCES_DIR
        args.type = 'Application'
        args.author = 'TestAuthor'
        args.name = None
        args.full_name = None
        args.tags = None
        args.description = None

        expected_manifest = {
            'Format': 'MuranoPL/1.0',
            'Type': 'Application',
            'Classes': {'io.murano.apps.test.APP': 'testapp.yaml'},
            'FullName': 'io.murano.apps.test.APP',
            'Name': 'APP',
            'Description': 'Description for the application is not provided',
            'Author': 'TestAuthor',
        }
        result_manifest = mpl_package.generate_manifest(args)
        self.check_dict_is_subset(expected_manifest, result_manifest)

    def test_generate_mpl_manifest_with_all_parameters(self):
        args = TestArgs()
        args.template = TEMPLATE
        args.classes_dir = CLASSES_DIR
        args.resources_dir = RESOURCES_DIR
        args.type = 'Application'
        args.name = 'test_name'
        args.author = 'TestAuthor'
        args.full_name = 'test.full.name.TestName'
        args.tags = ['test', 'tag', 'Heat']
        args.description = 'Test description'

        expected_manifest = {
            'Format': 'MuranoPL/1.0',
            'Type': 'Application',
            'Classes': {'io.murano.apps.test.APP': 'testapp.yaml'},
            'FullName': 'test.full.name.TestName',
            'Name': 'test_name',
            'Description': 'Test description',
            'Author': 'TestAuthor',
            'Tags': ['test', 'tag', 'Heat']
        }
        result_manifest = mpl_package.generate_manifest(args)
        self.check_dict_is_subset(expected_manifest, result_manifest)

    def test_generate_mpl_wrong_classes_dir(self):
        args = TestArgs()
        args.classes_dir = '/home/this/path/does/not/exist'
        expected = ("'--classes-dir' parameter should be a directory", )
        try:
            mpl_package.generate_manifest(args)
        except exceptions.CommandError as message:
            self.assertEqual(expected, message.args)

    def test_prepare_mpl_wrong_resources_dir(self):
        args = TestArgs()
        args.template = TEMPLATE
        args.classes_dir = CLASSES_DIR
        args.resources_dir = '/home/this/path/does/not/exist'
        args.type = 'Application'
        args.name = 'Test'
        args.tags = ''
        args.ui = UI
        args.logo = LOGO
        args.full_name = 'test.full.name.TestName'
        args.author = 'TestAuthor'
        args.description = 'Test description'

        expected = ("'--resources-dir' parameter should be a directory", )
        try:
            mpl_package.prepare_package(args)
        except exceptions.CommandError as message:
            self.assertEqual(expected, message.args)

    def test_prepare_mpl_package(self):
        args = TestArgs()
        args.template = TEMPLATE
        args.classes_dir = CLASSES_DIR
        args.resources_dir = RESOURCES_DIR
        args.type = 'Application'
        args.name = 'test_name'
        args.author = 'TestAuthor'
        args.full_name = 'test.full.name.TestName'
        args.tags = 'test, tag, Heat'
        args.description = 'Test description'
        args.ui = UI
        args.logo = LOGO
        prepared_files = ['UI', 'Classes', 'manifest.yaml',
                          'Resources', 'logo.png']
        package_dir = mpl_package.prepare_package(args)
        self.assertEqual(sorted(prepared_files),
                         sorted(os.listdir(package_dir)))
        shutil.rmtree(package_dir)
