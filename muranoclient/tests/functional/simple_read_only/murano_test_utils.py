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

import multiprocessing
import os
import shutil
import SimpleHTTPServer
import SocketServer
import tempfile
import time
import uuid

from muranoclient.tests.functional import muranoclient
from muranoclient.tests.functional.simple_read_only import utils
from tempest_lib.cli import output_parser


class CLIUtilsTestBase(muranoclient.ClientTestBase):
    """Basic methods for Murano CLI client."""

    def delete_murano_object(self, murano_object, obj_to_del):
        """Delete Murano object like environment, category
        or environment-template.
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
        """Create Murano object like environment, category
        or environment-template.
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

    @staticmethod
    def generate_name(prefix):
        """Generate name for objects."""
        suffix = uuid.uuid4().hex[:8]
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
            httpd = SocketServer.TCPServer(
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
