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

from http import server as SimpleHTTPServer
import json
import multiprocessing
import os
import shutil
import socketserver
import tempfile
import time

from oslo_utils import uuidutils
from tempest.lib.cli import output_parser
from tempest.lib import exceptions

from muranoclient.tests.functional.cli import utils
from muranoclient.tests.functional import muranoclient


class CLIUtilsTestBase(muranoclient.ClientTestBase):
    """Basic methods for Murano CLI client."""

    def delete_murano_object(self, murano_object, obj_to_del):
        """Delete Murano object

        Delete Murano object like environment, category or
        environment-template.
        """
        if obj_to_del not in self.listing('{0}-list'.format(murano_object)):
            return
        object_list = self.listing('{0}-delete'.format(murano_object),
                                   params=obj_to_del['ID'])
        start_time = time.time()
        while obj_to_del in self.listing('{0}-list'.format(murano_object)):
            if start_time - time.time() > 60:
                self.fail("{0} is not deleted in 60 seconds".
                          format(murano_object))
        return object_list

    def create_murano_object(self, murano_object, prefix_object_name):
        """Create Murano object

        Create Murano object like environment, category or
        environment-template.
        """
        object_name = self.generate_name(prefix_object_name)
        mrn_objects = self.listing('{0}-create'.format(murano_object),
                                   params=object_name)
        mrn_object = None
        for obj in mrn_objects:
            if object_name == obj['Name']:
                mrn_object = obj
                break
        if mrn_object is None:
            self.fail("Murano {0} has not been created!".format(murano_object))

        self.addCleanup(self.delete_murano_object, murano_object, mrn_object)
        return mrn_object

    def create_murano_object_parameter(self, murano_object, prefix_object_name,
                                       param):
        """Create Murano object

        Create Murano object like environment, category or
        environment-template.
        """
        object_name = self.generate_name(prefix_object_name)
        params = '{0} {1}'.format(param, object_name)

        mrn_objects = self.listing('{0}-create'.format(murano_object),
                                   params=params)
        mrn_object = None
        for obj in mrn_objects:
            if object_name == obj['Name']:
                mrn_object = obj
                break
        if mrn_object is None:
            self.fail("Murano {0} has not been created!".format(murano_object))

        self.addCleanup(self.delete_murano_object, murano_object, mrn_object)
        return mrn_object

    @staticmethod
    def generate_uuid():
        """Generate uuid for objects."""
        return uuidutils.generate_uuid(dashed=False)

    @staticmethod
    def generate_name(prefix):
        """Generate name for objects."""
        suffix = CLIUtilsTestBase.generate_uuid()[:8]
        return "{0}_{1}".format(prefix, suffix)

    def get_table_struct(self, command, params=""):
        """Get table structure i.e. header of table."""
        return output_parser.table(self.murano(command,
                                               params=params))['headers']

    def get_object(self, object_list, object_value):
        """"Get Murano object by value from list of Murano objects."""
        for obj in object_list:
            if object_value in obj.values():
                return obj

    def get_property_value(self, obj, prop):
        return [o['Value'] for o in obj
                if o['Property'] == '{0}'.format(prop)][0]


class TestSuiteRepository(CLIUtilsTestBase):

    def setUp(self):
        super(TestSuiteRepository, self).setUp()
        self.serve_dir = tempfile.mkdtemp(suffix="repo")
        self.app_name = self.generate_name("dummy_app")
        self.dummy_app_path = self._compose_app(name=self.app_name)

    def tearDown(self):
        super(TestSuiteRepository, self).tearDown()
        shutil.rmtree(self.serve_dir)

    def run_server(self):
        def serve_function():
            class Handler(SimpleHTTPServer.SimpleHTTPRequestHandler):
                pass
            os.chdir(self.serve_dir)
            httpd = socketserver.TCPServer(
                ("0.0.0.0", 8089),
                Handler, bind_and_activate=False)
            httpd.allow_reuse_address = True
            httpd.server_bind()
            httpd.server_activate()
            httpd.serve_forever()
        self.p = multiprocessing.Process(target=serve_function)
        self.p.start()

    def stop_server(self):
        self.p.terminate()

    def _compose_app(self, name, require=None):
        package_dir = os.path.join(self.serve_dir, 'apps/', name)
        shutil.copytree(os.path.join(os.path.dirname(
            os.path.realpath(__file__)), 'MockApp'), package_dir)

        app_name = utils.compose_package(
            name,
            os.path.join(package_dir, 'manifest.yaml'),
            package_dir,
            require=require,
            archive_dir=os.path.join(self.serve_dir, 'apps/'),
        )

        return app_name


class CLIUtilsTestPackagesBase(TestSuiteRepository):
    """Basic methods for Murano Packages CLI client."""

    def import_package(self, pkg_name, pkg_path, *args):
        """Create Murano dummy package and import it by url."""

        actions = ' '.join(args)
        params = '{0} {1}'.format(pkg_path, actions)
        package = self.listing('package-import', params=params)
        package = self.get_object(package, pkg_name)
        self.addCleanup(self.delete_murano_object, 'package', package)

        return package

    def prepare_file_with_obj_model(self, obj_model):
        temp_file = tempfile.NamedTemporaryFile(prefix="murano-obj-model",
                                                delete=False)
        self.addCleanup(os.remove, temp_file.name)

        with open(temp_file.name, 'w') as tf:
            tf.write(json.dumps([obj_model]))

        return temp_file.name

    def wait_deployment_result(self, env_id, timeout=180):
        start_time = time.time()

        env = self.listing('environment-show', params=env_id)
        env_status = self.get_property_value(env, 'status')

        expected_statuses = ['ready', 'deploying']

        while env_status != 'ready':
            if time.time() - start_time > timeout:
                msg = ("Environment exceeds timeout {0} to change state "
                       "to Ready. Environment: {1}".format(timeout, env))
                raise exceptions.TimeoutException(msg)

            env = self.listing('environment-show', params=env_id)
            env_status = self.get_property_value(env, 'status')

            if env_status not in expected_statuses:
                msg = ("Environment status %s is not in expected "
                       "statuses: %s" % (env_status, expected_statuses))
                raise exceptions.TempestException(msg)

            time.sleep(2)

        return True

    def prepare_bundle_with_non_existed_package(self):
        temp_file = tempfile.NamedTemporaryFile(mode='w',
                                                delete=False)
        self.addCleanup(os.remove, temp_file.name)

        with open(temp_file.name, 'w') as tf:
            tf.write(json.dumps({'Packages': [
                {'Name': 'first_app'},
                {'Name': 'second_app', 'Version': '1.0'}
            ]}))

        return temp_file.name

    def prepare_bundle_with_invalid_format(self):
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
        self.addCleanup(os.remove, temp_file.name)

        with open(temp_file.name, 'w') as tf:
            tf.write('Packages: [{Name: first_app}, {Name: second_app}]')

        return temp_file.name

    def deploy_environment(self, env_id, obj_model):
        session = self.listing('environment-session-create',
                               params=env_id)
        session_id = self.get_property_value(session, 'id')

        temp_file = self.prepare_file_with_obj_model(obj_model)

        self.listing('environment-apps-edit',
                     params='--session-id {0} {1} {2}'.
                     format(session_id, env_id, temp_file))

        self.listing('environment-deploy',
                     params='{0} --session-id {1}'.
                     format(env_id, session_id))

        result = self.wait_deployment_result(env_id)
        self.assertTrue(result)
