# Copyright (c) 2014 Mirantis, Inc.
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

import configparser
import os

from tempest.lib.cli import base


class ClientTestBase(base.ClientTestBase):

    def murano(self, action, flags='', params='',
               fail_ok=False, endpoint_type='publicURL', merge_stderr=True):
        flags += self.get_backend_flag()
        return self.clients.cmd_with_auth(
            'murano', action, flags, params, fail_ok, merge_stderr)

    def _get_clients(self):
        cli_dir = os.environ.get(
            'OS_MURANOCLIENT_EXEC_DIR',
            os.path.join(os.path.abspath('.'), '.tox/functional/bin'))

        self.username = os.environ.get('OS_USERNAME')
        self.password = os.environ.get('OS_PASSWORD')
        self.tenant_name = os.environ.get('OS_PROJECT_NAME',
                                          os.environ.get('OS_TENANT_NAME'))
        self.uri = os.environ.get('OS_AUTH_URL')
        config = configparser.RawConfigParser()
        if config.read('functional_creds.conf'):
            # the OR pattern means the environment is preferred for
            # override
            self.username = self.username or config.get('admin', 'user')
            self.password = self.password or config.get('admin', 'pass')
            self.tenant_name = self.tenant_name or config.get('admin',
                                                              'tenant')
            self.uri = self.uri or config.get('auth', 'uri')

        clients = base.CLIClient(
            username=self.username,
            password=self.password,
            tenant_name=self.tenant_name,
            uri=self.uri,
            cli_dir=cli_dir
        )
        return clients

    def listing(self, command, params=""):
        return self.parser.listing(self.murano(command, params=params))

    def get_value(self, need_field, known_field, known_value, somelist):
        for element in somelist:
            if element[known_field] == known_value:
                return element[need_field]

    @staticmethod
    def get_backend_flag():
        backend = os.environ.get('MURANO_PACKAGES_SERVICE', 'murano')
        backend_flag = " --murano-packages-service {0} ".format(backend)
        return backend_flag
