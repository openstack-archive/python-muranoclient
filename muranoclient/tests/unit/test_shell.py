#
#    Copyright (c) 2013 Mirantis, Inc.
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

import collections
import filecmp
import json
import logging
import os
import re
import shutil
import sys
import tempfile

import fixtures
from keystoneclient import fixture
from keystoneclient.fixture import v2 as ks_v2_fixture
from keystoneclient.fixture import v3 as ks_v3_fixture
import mock
from oslo_log import handlers
from oslo_log import log
import requests_mock
import six
from testtools import matchers

from muranoclient.common import exceptions as common_exceptions
from muranoclient.common import utils
from muranoclient.openstack.common.apiclient import exceptions
import muranoclient.shell
from muranoclient.tests.unit import base
from muranoclient.tests.unit import test_utils
from muranoclient.v1 import shell as v1_shell

make_pkg = test_utils.make_pkg

FIXTURE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                           'fixture_data'))
# RESULT_PACKAGE = os.path.join(FIXTURE_DIR, 'test-app.zip')

FAKE_ENV = {'OS_USERNAME': 'username',
            'OS_PASSWORD': 'password',
            'OS_TENANT_NAME': 'tenant_name',
            'OS_AUTH_URL': 'http://no.where/v2.0'}

FAKE_ENV2 = {'OS_USERNAME': 'username',
             'OS_PASSWORD': 'password',
             'OS_TENANT_ID': 'tenant_id',
             'OS_AUTH_URL': 'http://no.where/v2.0'}

FAKE_ENV_v3 = {'OS_USERNAME': 'username',
               'OS_PASSWORD': 'password',
               'OS_TENANT_ID': 'tenant_id',
               'OS_USER_DOMAIN_NAME': 'domain_name',
               'OS_AUTH_URL': 'http://no.where/v3'}


def _create_ver_list(versions):
    return {'versions': {'values': versions}}


class TestArgs(object):
    package_version = ''
    murano_repo_url = 'http://127.0.0.1'
    exists_action = ''
    dep_exists_action = ''
    is_public = False
    categories = []


class ShellTest(base.TestCaseShell):

    def make_env(self, exclude=None, fake_env=FAKE_ENV):
        env = dict((k, v) for k, v in fake_env.items() if k != exclude)
        self.useFixture(fixtures.MonkeyPatch('os.environ', env))


class ShellCommandTest(ShellTest):

    _msg_no_tenant_project = ('You must provide a project name or project'
                              ' id via --os-project-name, --os-project-id,'
                              ' env[OS_PROJECT_ID] or env[OS_PROJECT_NAME].'
                              ' You may use os-project and os-tenant'
                              ' interchangeably.',)

    def setUp(self):
        super(ShellCommandTest, self).setUp()

        def get_auth_endpoint(bound_self, args):
            return ('test', {})
        self.useFixture(fixtures.MonkeyPatch(
            'muranoclient.shell.MuranoShell._get_endpoint_and_kwargs',
            get_auth_endpoint))
        self.client = mock.MagicMock()

        # To prevent log descriptors from being closed during
        # shell tests set a custom StreamHandler
        self.logger = log.getLogger(None).logger
        self.logger.level = logging.DEBUG
        self.color_handler = handlers.ColorHandler(sys.stdout)
        self.logger.addHandler(self.color_handler)

    def tearDown(self):
        super(ShellTest, self).tearDown()
        self.logger.removeHandler(self.color_handler)

    def shell(self, argstr, exitcodes=(0,)):
        orig = sys.stdout
        orig_stderr = sys.stderr
        try:
            sys.stdout = six.StringIO()
            sys.stderr = six.StringIO()
            _shell = muranoclient.shell.MuranoShell()
            _shell.main(argstr.split())
        except SystemExit:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            self.assertIn(exc_value.code, exitcodes)
        finally:
            stdout = sys.stdout.getvalue()
            sys.stdout.close()
            sys.stdout = orig
            stderr = sys.stderr.getvalue()
            sys.stderr.close()
            sys.stderr = orig_stderr
        return (stdout, stderr)

    def register_keystone_discovery_fixture(self, mreq):
        v2_url = "http://no.where/v2.0"
        v2_version = fixture.V2Discovery(v2_url)
        mreq.register_uri('GET', v2_url, json=_create_ver_list([v2_version]),
                          status_code=200)

    def register_keystone_token_fixture(self, mreq):
        v2_token = ks_v2_fixture.Token(token_id='token')
        service = v2_token.add_service('application-catalog')
        service.add_endpoint('http://no.where', region='RegionOne')
        mreq.register_uri('POST',
                          'http://no.where/v2.0/tokens',
                          json=v2_token,
                          status_code=200)

    def test_help_unknown_command(self):
        self.assertRaises(exceptions.CommandError, self.shell, 'help foofoo')

    def test_help(self):
        required = [
            '.*?^usage: murano',
            '.*?^\s+package-create\s+Create an application package.',
            '.*?^See "murano help COMMAND" for help on a specific command',
        ]
        stdout, stderr = self.shell('help')
        for r in required:
            self.assertThat((stdout + stderr),
                            matchers.MatchesRegex(r, re.DOTALL | re.MULTILINE))

    def test_help_on_subcommand(self):
        required = [
            '.*?^usage: murano package-create',
            '.*?^Create an application package.',
        ]
        stdout, stderr = self.shell('help package-create')
        for r in required:
            self.assertThat((stdout + stderr),
                            matchers.MatchesRegex(r, re.DOTALL | re.MULTILINE))

    def test_help_no_options(self):
        required = [
            '.*?^usage: murano',
            '.*?^\s+package-create\s+Create an application package',
            '.*?^See "murano help COMMAND" for help on a specific command',
        ]
        stdout, stderr = self.shell('')
        for r in required:
            self.assertThat((stdout + stderr),
                            matchers.MatchesRegex(r, re.DOTALL | re.MULTILINE))

    def test_no_username(self):
        required = ('You must provide a username via either --os-username or '
                    'env[OS_USERNAME] or a token via --os-auth-token or '
                    'env[OS_AUTH_TOKEN]',)
        self.make_env(exclude='OS_USERNAME')
        try:
            self.shell('package-list')
        except exceptions.CommandError as message:
            self.assertEqual(required, message.args)
        else:
            self.fail('CommandError not raised')

    def test_no_tenant_name(self):
        required = self._msg_no_tenant_project
        self.make_env(exclude='OS_TENANT_NAME')
        try:
            self.shell('package-list')
        except exceptions.CommandError as message:
            self.assertEqual(required, message.args)
        else:
            self.fail('CommandError not raised')

    def test_no_tenant_id(self):
        required = self._msg_no_tenant_project
        self.make_env(exclude='OS_TENANT_ID', fake_env=FAKE_ENV2)
        try:
            self.shell('package-list')
        except exceptions.CommandError as message:
            self.assertEqual(required, message.args)
        else:
            self.fail('CommandError not raised')

    def test_no_auth_url(self):
        required = ('You must provide an auth url'
                    ' via either --os-auth-url or via env[OS_AUTH_URL]',)
        self.make_env(exclude='OS_AUTH_URL')
        try:
            self.shell('package-list')
        except exceptions.CommandError as message:
            self.assertEqual(required, message.args)
        else:
            self.fail('CommandError not raised')

    @mock.patch('muranoclient.v1.packages.PackageManager')
    @requests_mock.mock()
    def test_package_list(self, mock_package_manager, m_requests):
        self.client.packages = mock_package_manager()
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        self.shell('package-list')
        self.client.packages.filter.assert_called_once_with(
            include_disabled=False,
            limit=20,
            owned=False)

    @mock.patch('muranoclient.v1.packages.PackageManager')
    @requests_mock.mock()
    def test_package_list_with_limit(self, mock_package_manager, m_requests):
        self.client.packages = mock_package_manager()
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        self.shell('package-list --limit 10')
        self.client.packages.filter.assert_called_once_with(
            include_disabled=False,
            limit=10,
            owned=False)

    @mock.patch('muranoclient.v1.packages.PackageManager')
    @requests_mock.mock()
    def test_package_list_with_name(self, mock_package_manager, m_requests):
        self.client.packages = mock_package_manager()
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        self.shell('package-list --name mysql')
        self.client.packages.filter.assert_called_once_with(
            name='mysql',
            include_disabled=False,
            owned=False,
            limit=20)

    @mock.patch('muranoclient.v1.packages.PackageManager')
    @requests_mock.mock()
    def test_package_list_with_fqn(self, mock_package_manager, m_requests):
        self.client.packages = mock_package_manager()
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        self.shell('package-list --fqn mysql')
        self.client.packages.filter.assert_called_once_with(
            fqn='mysql',
            include_disabled=False,
            owned=False,
            limit=20)

    @mock.patch('muranoclient.v1.packages.PackageManager')
    @requests_mock.mock()
    def test_package_show(self, mock_package_manager, m_requests):
        self.client.packages = mock_package_manager()
        mock_package = mock.MagicMock()
        mock_package.class_definitions = ''
        mock_package.categories = ''
        mock_package.tags = ''
        mock_package.description = ''
        self.client.packages.get.return_value = mock_package
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        self.shell('package-show 1234')
        self.client.packages.get.assert_called_with('1234')

    @mock.patch('muranoclient.v1.packages.PackageManager')
    @requests_mock.mock()
    def test_package_update(self, mock_package_manager, m_requests):
        self.client.packages = mock_package_manager()
        mock_package = mock.MagicMock()
        mock_package.class_definitions = ''
        mock_package.categories = ''
        mock_package.tags = ''
        mock_package.description = ''
        self.client.packages.get.return_value = mock_package

        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)

        self.shell('package-update 123 --is-public true')
        self.shell('package-update 123 --is-public false')
        self.shell('package-update 123 --is-public false --enabled t')
        self.shell('package-update 123 --name foo --description bar')
        self.shell('package-update 123 --tags a')
        self.shell('package-update 123 --tags a ' +
                   '--is-public f --enabled f ' +
                   '--name foo ' +
                   '--description bar',)
        self.client.packages.update.assert_has_calls([
            mock.call('123', {'is_public': True}),
            mock.call('123', {'is_public': False}),
            mock.call('123', {'enabled': True, 'is_public': False}),
            mock.call('123', {'name': 'foo', 'description': 'bar'}),
            mock.call('123', {'tags': ['a']}),
            mock.call('123', {
                'tags': ['a'],
                'is_public': False,
                'enabled': False,
                'name': 'foo',
                'description': 'bar',
            }),
        ])

    @mock.patch('muranoclient.v1.packages.PackageManager')
    @requests_mock.mock()
    def test_package_delete(self, mock_package_manager, m_requests):
        self.client.packages = mock_package_manager()
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        self.shell('package-delete 1234 4321')
        self.client.packages.delete.assert_has_calls([
            mock.call('1234'), mock.call('4321')])
        self.assertEqual(2, self.client.packages.delete.call_count)

    @mock.patch('muranoclient.v1.sessions.SessionManager')
    @requests_mock.mock()
    def test_environment_session_create(self, mock_manager, m_requests):
        self.client.sessions = mock_manager()
        self.client.sessions.configure.return_value.id = '123'
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        self.shell('environment-session-create 1234')
        self.client.sessions.configure.assert_has_calls([
            mock.call('1234')])

    @mock.patch('muranoclient.v1.environments.EnvironmentManager')
    @requests_mock.mock()
    def test_environment_create(self, mock_manager, m_requests):
        self.client.environments = mock_manager()
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)

        self.shell('environment-create foo')
        self.client.environments.create.assert_has_calls(
            [mock.call({'name': 'foo', 'region': None})])
        self.client.environments.create.reset_mock()
        self.shell('environment-create --join-net 123 foo --region RegionOne')
        cc = self.client.environments.create
        expected_call = mock.call({
            'defaultNetworks': {
                'environment': {
                    'internalNetworkName': '123',
                    '?': {
                        'type': 'io.murano.resources.ExistingNeutronNetwork',
                        'id': mock.ANY
                    }
                },
                'flat': None
            },
            'name': 'foo',
            'region': 'RegionOne'
        })
        self.assertEqual(expected_call, cc.call_args)

    @mock.patch('muranoclient.v1.environments.EnvironmentManager')
    @requests_mock.mock()
    def test_environment_list(self, mock_manager, m_requests):
        self.client.environments = mock_manager()
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)

        self.shell('environment-list')
        self.client.environments.list.assert_called_once_with(False)

        self.client.environments.list.reset_mock()
        self.shell('environment-list --all-tenants')
        self.client.environments.list.assert_called_once_with(True)

    @mock.patch('muranoclient.v1.environments.EnvironmentManager')
    @requests_mock.mock()
    def test_environment_delete(self, mock_manager, m_requests):
        self.client.environments = mock_manager()
        self.client.environments.find.return_value.id = '123'
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        self.shell('environment-delete env1')
        self.client.environments.find.assert_has_calls([
            mock.call(name='env1')
        ])
        self.client.environments.delete.assert_has_calls([
            mock.call('123', False)
        ])

    @mock.patch('muranoclient.v1.environments.EnvironmentManager')
    @requests_mock.mock()
    def test_environment_delete_with_abandon(self, mock_manager, m_requests):
        self.client.environments = mock_manager()
        self.client.environments.find.return_value.id = '123'
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        self.shell('environment-delete env1 --abandon')
        self.client.environments.find.assert_has_calls([
            mock.call(name='env1')
        ])
        self.client.environments.delete.assert_has_calls([
            mock.call('123', True)
        ])

    @mock.patch('muranoclient.v1.environments.EnvironmentManager')
    @requests_mock.mock()
    def test_environment_rename(self, mock_manager, m_requests):
        self.client.environments = mock_manager()
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        self.shell('environment-rename old-name-or-id new-name')
        self.client.environments.find.assert_called_once_with(
            name='old-name-or-id')
        self.assertEqual(1, self.client.environments.update.call_count)

    @mock.patch('muranoclient.v1.environments.EnvironmentManager')
    @requests_mock.mock()
    def test_environment_show(self, mock_manager, m_requests):
        self.client.environments = mock_manager()
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        self.shell('environment-show env-id-or-name')
        self.client.environments.find.assert_called_once_with(
            name='env-id-or-name')

    @mock.patch('muranoclient.v1.environments.EnvironmentManager')
    @mock.patch('muranoclient.v1.sessions.SessionManager')
    @requests_mock.mock()
    def test_environment_deploy(self, mock_manager, env_manager, m_requests):
        self.client.sessions = mock_manager()
        self.client.environments = env_manager()
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        self.shell('environment-deploy 12345 --session-id 54321')
        self.client.sessions.deploy.assert_called_once_with(
            '12345', '54321')

    @mock.patch('muranoclient.v1.environments.EnvironmentManager')
    @requests_mock.mock()
    def test_environment_show_session(self, mock_manager, m_requests):
        self.client.environments = mock_manager()
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        self.shell('environment-show 12345 --session-id 12345')
        self.client.environments.get.assert_called_once_with(
            12345, session_id='12345')

    @mock.patch('muranoclient.v1.actions.ActionManager')
    @requests_mock.mock()
    def test_environment_action_call(self, mock_manager, m_requests):
        self.client.actions = mock_manager()
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        self.shell('environment-action-call 12345 --action-id 54321')
        self.client.actions.call.assert_called_once_with(
            '12345', '54321', arguments={})

    @mock.patch('muranoclient.v1.actions.ActionManager')
    @requests_mock.mock()
    def test_environment_action_call_args(self, mock_manager, m_requests):
        self.client.actions = mock_manager()
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        self.shell("""environment-action-call 12345 --action-id 54321
                   --arguments foo=bar
                   dictArg={"key1":"value1","key2":"value2"}
                   listArg=["item1","item2","item3"]
                   nullArg=null
                   stringArg="null"
                   intArg=5
                   compoundArg=["foo",14,{"key1":null,"key2":8}]""")
        self.client.actions.call.assert_called_once_with(
            '12345', '54321', arguments={
                'foo': 'bar',
                'dictArg': {u'key1': u'value1', u'key2': u'value2'},
                'listArg': [u'item1', u'item2', u'item3'],
                'nullArg': None,
                'stringArg': u'null',
                'intArg': 5,
                'compoundArg': [u'foo', 14, {u'key1': None, u'key2': 8}]
            })

    @mock.patch('muranoclient.v1.actions.ActionManager')
    @requests_mock.mock()
    def test_environment_action_get_result(self, mock_manager, m_requests):
        self.client.actions = mock_manager()
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        self.shell('environment-action-get-result 12345 --task-id 54321')
        self.client.actions.get_result.assert_called_once_with(
            '12345', '54321')

    @mock.patch('muranoclient.v1.static_actions.StaticActionManager')
    @requests_mock.mock()
    def test_static_action_call_basic(self, mock_manager, m_requests):
        self.client.static_actions = mock_manager()
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        self.shell('static-action-call class.name method.name')
        self.client.static_actions.call.assert_called_once_with({
            "className": 'class.name',
            "methodName": 'method.name',
            "packageName": None,
            "classVersion": '=0',
            "parameters": {}
        })

    @mock.patch('muranoclient.v1.static_actions.StaticActionManager')
    @requests_mock.mock()
    def test_static_action_call_full(self, mock_manager, m_requests):
        self.client.static_actions = mock_manager()
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        self.shell('static-action-call class.name method.name '
                   '--package-name package.name --class-version ">1"')
        self.client.static_actions.call.assert_called_once_with({
            "className": 'class.name',
            "methodName": 'method.name',
            "packageName": 'package.name',
            "classVersion": '">1"',
            "parameters": {}
        })

    @mock.patch('muranoclient.v1.static_actions.StaticActionManager')
    @requests_mock.mock()
    def test_static_action_call_string_args(self, mock_manager, m_requests):
        self.client.static_actions = mock_manager()
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        self.shell('static-action-call class.name method.name '
                   '--arguments food=spam parrot=dead')
        self.client.static_actions.call.assert_called_once_with({
            "className": 'class.name',
            "methodName": 'method.name',
            "packageName": None,
            "classVersion": '=0',
            "parameters": {'food': 'spam', 'parrot': 'dead'}
        })

    @mock.patch('muranoclient.v1.static_actions.StaticActionManager')
    @requests_mock.mock()
    def test_static_action_call_json_args(self, mock_manager, m_requests):
        self.client.static_actions = mock_manager()
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        self.shell("""static-action-call class.name method.name
                   --arguments
                   dictArg={"key1":"value1","key2":"value2"}
                   listArg=["item1","item2","item3"]
                   nullArg=null
                   stringArg="null"
                   intArg=5
                   compoundArg=["foo",14,{"key1":null,"key2":8}]""")
        self.client.static_actions.call.assert_called_once_with({
            "className": 'class.name',
            "methodName": 'method.name',
            "packageName": None,
            "classVersion": '=0',
            "parameters": {
                'dictArg': {u'key1': u'value1', u'key2': u'value2'},
                'listArg': [u'item1', u'item2', u'item3'],
                'nullArg': None,
                'stringArg': u'null',
                'intArg': 5,
                'compoundArg': [u'foo', 14, {u'key1': None, u'key2': 8}]
            }
        })

    @mock.patch('muranoclient.v1.schemas.SchemaManager')
    @requests_mock.mock()
    def test_class_schema(self, mock_manager, m_requests):
        self.client.schemas = mock_manager()
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        self.shell('class-schema class.name')
        self.client.schemas.get.assert_called_once_with(
            'class.name', [],
            package_name=None,
            class_version='=0'
        )

    @mock.patch('muranoclient.v1.schemas.SchemaManager')
    @requests_mock.mock()
    def test_class_schema_with_methods(self, mock_manager, m_requests):
        self.client.schemas = mock_manager()
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        self.shell('class-schema class.name method1 method2')
        self.client.schemas.get.assert_called_once_with(
            'class.name', ['method1', 'method2'],
            package_name=None,
            class_version='=0'
        )

    @mock.patch('muranoclient.v1.schemas.SchemaManager')
    @requests_mock.mock()
    def test_class_schema_full(self, mock_manager, m_requests):
        self.client.schemas = mock_manager()
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        self.shell('class-schema class.name method1 method2 '
                   '--class-version >1.2.3 --package-name foo.bar')
        self.client.schemas.get.assert_called_once_with(
            'class.name', ['method1', 'method2'],
            package_name='foo.bar',
            class_version='>1.2.3'
        )

    @mock.patch('muranoclient.v1.templates.EnvTemplateManager')
    @requests_mock.mock()
    def test_env_template_delete(self, mock_manager, m_requests):
        self.client.env_templates = mock_manager()
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        self.shell('env-template-delete env1 env2')
        self.client.env_templates.delete.assert_has_calls([
            mock.call('env1'), mock.call('env2')])

    @mock.patch('muranoclient.v1.templates.EnvTemplateManager')
    @requests_mock.mock()
    def test_env_template_create(self, mock_manager, m_requests):
        self.client.env_templates = mock_manager()
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        self.shell('env-template-create env-name')
        self.client.env_templates.create.assert_called_once_with(
            {'name': 'env-name', 'is_public': False})

    @mock.patch('muranoclient.v1.templates.EnvTemplateManager')
    @requests_mock.mock()
    def test_env_template_create_public(self, mock_manager, m_requests):
        self.client.env_templates = mock_manager()
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        self.shell('env-template-create --is-public env-name')
        self.client.env_templates.create.assert_called_once_with(
            {'name': 'env-name', 'is_public': True})

    @mock.patch('muranoclient.v1.templates.EnvTemplateManager')
    @requests_mock.mock()
    def test_env_template_show(self, mock_manager, m_requests):
        self.client.env_templates = mock_manager()
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        self.shell('env-template-show env-id')
        self.client.env_templates.get.assert_called_once_with('env-id')

    @mock.patch('muranoclient.v1.templates.EnvTemplateManager')
    @requests_mock.mock()
    def test_env_template_create_env(self, mock_manager, m_requests):
        self.client.env_templates = mock_manager()
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        self.shell('env-template-create-env env-id env-name')
        self.client.env_templates.create_env.\
            assert_called_once_with('env-id', 'env-name')

    @mock.patch('muranoclient.v1.templates.EnvTemplateManager')
    @requests_mock.mock()
    def test_env_template_clone(self, mock_manager, m_requests):
        self.client.env_templates = mock_manager()
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        self.shell('env-template-clone env-id env-name')
        self.client.env_templates.clone.assert_called_once_with(
            'env-id', 'env-name')

    @mock.patch('muranoclient.v1.environments.EnvironmentManager')
    @mock.patch('muranoclient.v1.deployments.DeploymentManager')
    @requests_mock.mock()
    def test_deployments_show(self, mock_deployment_manager, mock_env_manager,
                              m_requests):
        self.client.deployments = mock_deployment_manager()
        self.client.environments = mock_env_manager()
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        self.shell('deployment-list env-id-or-name')
        self.client.environments.find.assert_called_once_with(
            name='env-id-or-name')
        self.assertEqual(1, self.client.deployments.list.call_count)

    @mock.patch('muranoclient.v1.services.ServiceManager')
    @mock.patch('muranoclient.v1.environments.EnvironmentManager')
    @requests_mock.mock()
    def test_environment_apps_edit(self, mock_env_manager, mock_services,
                                   m_requests):
        self.client.environments = mock_env_manager()
        self.client.services = mock_services()
        fake = collections.namedtuple('fakeEnv', 'services')
        self.client.environments.get.side_effect = [
            fake(services=[
                {'?': {'name': "foo"}}
            ]),
        ]

        temp_file = tempfile.NamedTemporaryFile(prefix="murano-test", mode='w')
        json.dump([
            {'op': 'replace', 'path': '/0/?/name',
                'value': "dummy"
             }
        ], temp_file)
        temp_file.file.flush()

        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)

        self.shell('environment-apps-edit 12345 {0} --session-id 4321'.format(
            temp_file.name))

        self.client.services.put.assert_called_once_with(
            '12345',
            session_id='4321',
            path='/',
            data=[{'?': {'name': 'dummy'}}]
        )

    @mock.patch('muranoclient.v1.services.ServiceManager')
    @requests_mock.mock()
    def test_app_show(self, mock_services, m_requests):
        self.client.services = mock_services()
        mock_app = mock.MagicMock()
        mock_app.name = "app_name"
        setattr(mock_app, '?', {'type': 'app_type', 'id': 'app_id'})
        self.client.services.list.return_value = [mock_app]
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        result = self.shell('app-show env-id')
        required = ['Id', 'Name', 'Type', 'app_id', 'app_name', 'app_type']
        for r in required:
            self.assertIn(r, result[0])
        self.client.services.list.assert_called_once_with('env-id')

    @mock.patch('muranoclient.v1.services.ServiceManager')
    @requests_mock.mock()
    def test_app_show_empty_list(self, mock_services, m_requests):
        self.client.services = mock_services()
        self.client.services.list.return_value = []
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        result = self.shell('app-show env-id')
        required = ['Id', 'Name', 'Type']
        for r in required:
            self.assertIn(r, result[0])
        self.client.services.list.assert_called_once_with('env-id')

    @mock.patch('muranoclient.v1.services.ServiceManager')
    @requests_mock.mock()
    def test_app_show_with_path(self, mock_services, m_requests):
        self.client.services = mock_services()
        mock_app = mock.MagicMock()
        mock_app.name = "app_name"
        setattr(mock_app, '?', {'type': 'app_type', 'id': 'app_id'})
        self.client.services.get.return_value = mock_app
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        result = self.shell('app-show env-id --path app-id')
        required = ['Property', 'Value']
        for r in required:
            self.assertIn(r, result[0])
        self.client.services.get.assert_called_once_with('env-id', '/app-id')

    @mock.patch('muranoclient.v1.categories.CategoryManager')
    @requests_mock.mock()
    def test_category_list(self, mock_manager, m_requests):
        self.client.categories = mock_manager()
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        result = self.shell('category-list')
        required = ['ID', 'Name']
        for r in required:
            self.assertIn(r, result[0])
        self.client.categories.list.assert_called_once_with()

    @mock.patch('muranoclient.v1.packages.PackageManager')
    @mock.patch('muranoclient.v1.categories.CategoryManager')
    @requests_mock.mock()
    def test_category_show(self, category_manager, pkg_manager, m_requests):
        self.client.packages = pkg_manager()
        self.client.categories = category_manager()
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        result = self.shell('category-show category-id')
        required = ['Property', 'Value', 'id', 'name', 'packages']
        for r in required:
            self.assertIn(r, result[0])
        self.client.categories.get.assert_called_once_with('category-id')

    @mock.patch('muranoclient.v1.categories.CategoryManager')
    @requests_mock.mock()
    def test_category_create(self, mock_manager, m_requests):
        self.client.categories = mock_manager()
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        result = self.shell('category-create category-name')
        required = ['ID', 'Name']
        for r in required:
            self.assertIn(r, result[0])
        self.client.categories.add.assert_called_once_with(
            {'name': 'category-name'})

    @mock.patch('muranoclient.v1.categories.CategoryManager')
    @requests_mock.mock()
    def test_category_delete(self, mock_manager, m_requests):
        self.client.categories = mock_manager()
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        result = self.shell('category-delete category-id')
        required = ['ID', 'Name']
        for r in required:
            self.assertIn(r, result[0])
        self.client.categories.delete.assert_called_once_with('category-id')

        self.client.categories.delete.side_effect =\
            common_exceptions.HTTPNotFound()
        ex = self.assertRaises(exceptions.CommandError, self.shell,
                               'category-delete category-id')
        expected = 'Unable to find and delete any of the specified categories.'
        self.assertEqual(expected, six.text_type(ex))


class ShellPackagesOperations(ShellCommandTest):
    @requests_mock.mock()
    def test_create_hot_based_package(self, m_requests):
        self.useFixture(fixtures.MonkeyPatch(
            'muranoclient.v1.client.Client', mock.MagicMock))
        heat_template = os.path.join(FIXTURE_DIR, 'heat-template.yaml')
        logo = os.path.join(FIXTURE_DIR, 'logo.png')
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        with tempfile.NamedTemporaryFile() as f:
            RESULT_PACKAGE = f.name
            c = "package-create --template={0} --output={1} -l={2}".format(
                heat_template, RESULT_PACKAGE, logo)
            stdout, stderr = self.shell(c)
            matchers.MatchesRegex((stdout + stderr),
                                  "Application package "
                                  "is available at {0}".format(RESULT_PACKAGE))

    @requests_mock.mock()
    def test_create_mpl_package(self, m_requests):
        self.useFixture(fixtures.MonkeyPatch(
            'muranoclient.v1.client.Client', mock.MagicMock))
        classes_dir = os.path.join(FIXTURE_DIR, 'test-app', 'Classes')
        resources_dir = os.path.join(FIXTURE_DIR, 'test-app', 'Resources')
        ui = os.path.join(FIXTURE_DIR, 'test-app', 'ui.yaml')
        self.make_env()
        self.register_keystone_discovery_fixture(m_requests)
        self.register_keystone_token_fixture(m_requests)
        with tempfile.NamedTemporaryFile() as f:
            RESULT_PACKAGE = f.name
            stdout, stderr = self.shell(
                "package-create  -c={0} -r={1} -u={2} -o={3}".format(
                    classes_dir, resources_dir, ui, RESULT_PACKAGE))
            matchers.MatchesRegex((stdout + stderr),
                                  "Application package "
                                  "is available at {0}".format(RESULT_PACKAGE))

    @mock.patch('muranoclient.common.utils.Package.from_file')
    def test_package_import(self, from_file):
        args = TestArgs()
        with tempfile.NamedTemporaryFile() as f:
            RESULT_PACKAGE = f.name
            args.filename = [RESULT_PACKAGE]
            args.categories = ['Cat1', 'Cat2 with space']
            args.is_public = True

            pkg = make_pkg({'FullName': RESULT_PACKAGE})
            from_file.return_value = utils.Package(utils.File(pkg))

            v1_shell.do_package_import(self.client, args)

            self.client.packages.create.assert_called_once_with({
                'categories': ['Cat1', 'Cat2 with space'],
                'is_public': True
            }, {RESULT_PACKAGE: mock.ANY},)

    def _test_conflict(self,
                       packages, from_file, raw_input_mock,
                       input_action, exists_action=''):
        packages.create = mock.MagicMock(
            side_effect=[common_exceptions.HTTPConflict("Conflict"), None])

        packages.filter.return_value = [mock.Mock(id='test_id')]

        raw_input_mock.return_value = input_action
        args = TestArgs()
        args.exists_action = exists_action
        with tempfile.NamedTemporaryFile() as f:
            args.filename = [f.name]

            pkg = make_pkg({'FullName': f.name})
            from_file.return_value = utils.Package(utils.File(pkg))

            v1_shell.do_package_import(self.client, args)
            return f.name

    @mock.patch('six.moves.input')
    @mock.patch('muranoclient.common.utils.Package.from_file')
    def test_package_import_conflict_skip(self, from_file, raw_input_mock):

        name = self._test_conflict(
            self.client.packages,
            from_file,
            raw_input_mock,
            's',
        )

        self.client.packages.create.assert_called_once_with({
            'is_public': False,
        }, {name: mock.ANY},)

    @mock.patch('six.moves.input')
    @mock.patch('muranoclient.common.utils.Package.from_file')
    def test_package_import_conflict_skip_ea(self, from_file, raw_input_mock):

        name = self._test_conflict(
            self.client.packages,
            from_file,
            raw_input_mock,
            '',
            exists_action='s',
        )

        self.client.packages.create.assert_called_once_with({
            'is_public': False,
        }, {name: mock.ANY},)
        self.assertFalse(raw_input_mock.called)

    @mock.patch('six.moves.input')
    @mock.patch('muranoclient.common.utils.Package.from_file')
    def test_package_import_conflict_abort(self, from_file, raw_input_mock):

        self.assertRaises(SystemExit, self._test_conflict,
                          self.client.packages,
                          from_file,
                          raw_input_mock,
                          'a',
                          )

        self.client.packages.create.assert_called_once_with({
            'is_public': False,
        }, mock.ANY,)

    @mock.patch('six.moves.input')
    @mock.patch('muranoclient.common.utils.Package.from_file')
    def test_package_import_conflict_abort_ea(self,
                                              from_file, raw_input_mock):

        self.assertRaises(SystemExit, self._test_conflict,
                          self.client.packages,
                          from_file,
                          raw_input_mock,
                          '',
                          exists_action='a',
                          )

        self.client.packages.create.assert_called_once_with({
            'is_public': False,
        }, mock.ANY,)
        self.assertFalse(raw_input_mock.called)

    @mock.patch('six.moves.input')
    @mock.patch('muranoclient.common.utils.Package.from_file')
    def test_package_import_conflict_update(self, from_file, raw_input_mock):

        name = self._test_conflict(
            self.client.packages,
            from_file,
            raw_input_mock,
            'u',
        )

        self.client.packages.delete.assert_called_once_with('test_id')

        self.client.packages.create.assert_has_calls(
            [
                mock.call({'is_public': False}, {name: mock.ANY},),
                mock.call({'is_public': False}, {name: mock.ANY},)
            ], any_order=True,
        )
        self.assertEqual(2, self.client.packages.create.call_count)

    @mock.patch('six.moves.input')
    @mock.patch('muranoclient.common.utils.Package.from_file')
    def test_package_import_conflict_update_ea(self,
                                               from_file, raw_input_mock):

        name = self._test_conflict(
            self.client.packages,
            from_file,
            raw_input_mock,
            '',
            exists_action='u',
        )

        self.client.packages.delete.assert_called_once_with('test_id')

        self.client.packages.create.assert_has_calls(
            [
                mock.call({'is_public': False}, {name: mock.ANY},),
                mock.call({'is_public': False}, {name: mock.ANY},)
            ], any_order=True,
        )
        self.assertEqual(2, self.client.packages.create.call_count)
        self.assertFalse(raw_input_mock.called)

    def _test_conflict_dep(self,
                           packages, from_file,
                           dep_exists_action=''):
        packages.create = mock.MagicMock(
            side_effect=[common_exceptions.HTTPConflict("Conflict"),
                         common_exceptions.HTTPConflict("Conflict"),
                         None])

        packages.filter.return_value = [mock.Mock(id='test_id')]

        args = TestArgs()
        args.exists_action = 's'
        args.dep_exists_action = dep_exists_action
        args.filename = ['first_app']

        pkg1 = make_pkg(
            {'FullName': 'first_app', 'Require': {'second_app': '1.0'}, })
        pkg2 = make_pkg({'FullName': 'second_app', })

        def side_effect(name):
            if 'first_app' in name:
                return utils.Package(utils.File(pkg1))
            if 'second_app' in name:
                return utils.Package(utils.File(pkg2))

        from_file.side_effect = side_effect

        v1_shell.do_package_import(self.client, args)

    @mock.patch('muranoclient.common.utils.Package.from_file')
    def test_package_import_conflict_dep_skip_ea(self, from_file):
        self._test_conflict_dep(
            self.client.packages,
            from_file,
            dep_exists_action='s',
        )

        self.client.packages.create.assert_has_calls(
            [
                mock.call({'is_public': False}, {'first_app': mock.ANY}),
                mock.call({'is_public': False}, {'second_app': mock.ANY}),
            ], any_order=True,
        )

        self.assertEqual(2, self.client.packages.create.call_count)

    @mock.patch('muranoclient.common.utils.Package.from_file')
    def test_package_import_conflict_dep_abort_ea(self, from_file):
        self.assertRaises(SystemExit, self._test_conflict_dep,
                          self.client.packages,
                          from_file,
                          dep_exists_action='a',
                          )

        self.client.packages.create.assert_called_with({
            'is_public': False,
        }, {'second_app': mock.ANY},)

    @mock.patch('muranoclient.common.utils.Package.from_file')
    def test_package_import_conflict_dep_update_ea(self, from_file):
        self._test_conflict_dep(
            self.client.packages,
            from_file,
            dep_exists_action='u',
        )

        self.assertEqual(True, self.client.packages.delete.called)

        self.client.packages.create.assert_has_calls(
            [
                mock.call({'is_public': False}, {'first_app': mock.ANY}),
                mock.call({'is_public': False}, {'second_app': mock.ANY}),
                mock.call({'is_public': False}, {'second_app': mock.ANY}),
            ], any_order=True,
        )

        self.assertEqual(True, self.client.packages.create.call_count > 2)
        self.assertEqual(True, self.client.packages.create.call_count < 5)

    @mock.patch('muranoclient.common.utils.Package.from_file')
    def test_package_import_no_categories(self, from_file):
        args = TestArgs()

        with tempfile.NamedTemporaryFile() as f:
            RESULT_PACKAGE = f.name
            pkg = make_pkg({'FullName': RESULT_PACKAGE})
            from_file.return_value = utils.Package(utils.File(pkg))

            args.filename = [RESULT_PACKAGE]
            args.categories = None
            args.is_public = False

            v1_shell.do_package_import(self.client, args)

            self.client.packages.create.assert_called_once_with(
                {'is_public': False},
                {RESULT_PACKAGE: mock.ANY},
            )

    @requests_mock.mock()
    @mock.patch('muranoclient.common.utils.Package.from_file')
    def test_package_import_url(self, rm, from_file):
        args = TestArgs()
        args.filename = ["http://127.0.0.1/test_package.zip"]
        args.categories = None
        args.is_public = False

        pkg = make_pkg({'FullName': 'test_package'})
        from_file.return_value = utils.Package(utils.File(pkg))

        rm.get(args.filename[0], body=make_pkg({'FullName': 'test_package'}))

        v1_shell.do_package_import(self.client, args)

        self.client.packages.create.assert_called_once_with(
            {'is_public': False},
            {'test_package': mock.ANY},
        )

    @requests_mock.mock()
    @mock.patch('muranoclient.common.utils.Package.from_file')
    def test_package_import_by_name(self, rm, from_file):
        args = TestArgs()

        args.filename = ["io.test.apps.test_application"]
        args.categories = None
        args.is_public = False
        args.murano_repo_url = "http://127.0.0.1"

        pkg = make_pkg({'FullName': args.filename[0]})
        from_file.return_value = utils.Package(utils.File(pkg))

        rm.get(args.murano_repo_url + '/apps/' + args.filename[0] + '.zip',
               body=make_pkg({'FullName': 'first_app'}))

        v1_shell.do_package_import(self.client, args)

        self.assertTrue(self.client.packages.create.called)
        self.client.packages.create.assert_called_once_with(
            {'is_public': False},
            {args.filename[0]: mock.ANY},
        )

    @requests_mock.mock()
    def test_package_import_multiple(self, rm):
        args = TestArgs()

        args.filename = ["io.test.apps.test_application",
                         "http://127.0.0.1/test_app2.zip", ]
        args.categories = None
        args.is_public = False
        args.murano_repo_url = "http://127.0.0.1"

        rm.get(args.murano_repo_url + '/apps/' + args.filename[0] + '.zip',
               body=make_pkg({'FullName': 'first_app'}))

        rm.get(args.filename[1],
               body=make_pkg({'FullName': 'second_app'}))

        v1_shell.do_package_import(self.client, args)

        self.assertTrue(self.client.packages.create.called)

        self.client.packages.create.assert_has_calls(
            [
                mock.call({'is_public': False}, {'first_app': mock.ANY}),
                mock.call({'is_public': False}, {'second_app': mock.ANY}),
            ], any_order=True,
        )

    @requests_mock.mock()
    def test_import_bundle_by_name(self, m):
        """Asserts bundle import calls packages create once for each pkg."""
        pkg1 = make_pkg({'FullName': 'first_app'})
        pkg2 = make_pkg({'FullName': 'second_app'})

        m.get(TestArgs.murano_repo_url + '/apps/first_app.zip', body=pkg1)
        m.get(TestArgs.murano_repo_url + '/apps/second_app.1.0.zip',
              body=pkg2)
        s = six.StringIO()
        bundle_contents = {'Packages': [
            {'Name': 'first_app'},
            {'Name': 'second_app', 'Version': '1.0'}
        ]}
        json.dump(bundle_contents, s)
        s = six.BytesIO(s.getvalue().encode('ascii'))

        m.get(TestArgs.murano_repo_url + '/bundles/test_bundle.bundle',
              body=s)

        args = TestArgs()
        args.filename = ["test_bundle"]

        v1_shell.do_bundle_import(self.client, args)

        self.client.packages.create.assert_has_calls(
            [
                mock.call({'is_public': False}, {'first_app': mock.ANY}),
                mock.call({'is_public': False}, {'second_app': mock.ANY}),
            ], any_order=True,
        )

    @requests_mock.mock()
    def test_import_bundle_dependencies(self, m):
        """Test bundle import calls

        Asserts bundle import calls packages create once for each pkg,
        including dependencies.
        """
        pkg1 = make_pkg(
            {'FullName': 'first_app', 'Require': {'second_app': '1.0'}, })
        pkg2 = make_pkg({'FullName': 'second_app'})

        m.get(TestArgs.murano_repo_url + '/apps/first_app.zip', body=pkg1)
        m.get(TestArgs.murano_repo_url + '/apps/second_app.1.0.zip',
              body=pkg2)

        s = six.StringIO()
        # bundle only contains 1st package
        bundle_contents = {'Packages': [
            {'Name': 'first_app'},
        ]}
        json.dump(bundle_contents, s)
        s = six.BytesIO(s.getvalue().encode('ascii'))

        m.get(TestArgs.murano_repo_url + '/bundles/test_bundle.bundle',
              body=s)

        args = TestArgs()
        args.filename = ["test_bundle"]

        v1_shell.do_bundle_import(self.client, args)

        self.client.packages.create.assert_has_calls(
            [
                mock.call({'is_public': False}, {'first_app': mock.ANY}),
                mock.call({'is_public': False}, {'second_app': mock.ANY}),
            ], any_order=True,
        )

    @requests_mock.mock()
    def test_import_bundle_by_url(self, m):
        """Asserts bundle import calls packages create once for each pkg."""
        pkg1 = make_pkg({'FullName': 'first_app'})
        pkg2 = make_pkg({'FullName': 'second_app'})

        m.get(TestArgs.murano_repo_url + '/apps/first_app.zip', body=pkg1)
        m.get(TestArgs.murano_repo_url + '/apps/second_app.1.0.zip',
              body=pkg2)
        s = six.StringIO()
        bundle_contents = {'Packages': [
            {'Name': 'first_app'},
            {'Name': 'second_app', 'Version': '1.0'}
        ]}
        json.dump(bundle_contents, s)
        s = six.BytesIO(s.getvalue().encode('ascii'))

        url = 'http://127.0.0.2/test_bundle.bundle'
        m.get(url, body=s)

        args = TestArgs()
        args.filename = [url]

        v1_shell.do_bundle_import(self.client, args)

        self.client.packages.create.assert_has_calls(
            [
                mock.call({'is_public': False}, {'first_app': mock.ANY}),
                mock.call({'is_public': False}, {'second_app': mock.ANY}),
            ], any_order=True,
        )

    @requests_mock.mock()
    def test_import_bundle_wrong_url(self, m):
        url = 'http://127.0.0.2/test_bundle.bundle'
        m.get(url, status_code=404)

        args = TestArgs()
        args.filename = [url]

        v1_shell.do_bundle_import(self.client, args)
        self.assertFalse(self.client.packages.create.called)

    @requests_mock.mock()
    def test_import_bundle_no_bundle(self, m):
        url = 'http://127.0.0.1/bundles/test_bundle.bundle'
        m.get(url, status_code=404)

        args = TestArgs()
        args.filename = ["test_bundle"]

        v1_shell.do_bundle_import(self.client, args)
        self.assertFalse(self.client.packages.create.called)

    @requests_mock.mock()
    def test_import_local_bundle(self, m):
        """Asserts local bundles are first searched locally."""
        tmp_dir = tempfile.mkdtemp()
        bundle_file = os.path.join(tmp_dir, 'bundle.bundle')
        with open(os.path.join(tmp_dir, 'bundle.bundle'), 'w') as f:

            bundle_contents = {'Packages': [
                {'Name': 'first_app'},
                {'Name': 'second_app', 'Version': '1.0'}
            ]}
            json.dump(bundle_contents, f)

        pkg1 = make_pkg({'FullName': 'first_app',
                         'Require': {'third_app': None}})
        pkg2 = make_pkg({'FullName': 'second_app'})
        pkg3 = make_pkg({'FullName': 'third_app'})
        with open(os.path.join(tmp_dir, 'first_app'), 'wb') as f:
            f.write(pkg1.read())
        with open(os.path.join(tmp_dir, 'third_app'), 'wb') as f:
            f.write(pkg3.read())

        m.get(TestArgs.murano_repo_url + '/apps/first_app.zip',
              status_code=404)
        m.get(TestArgs.murano_repo_url + '/apps/second_app.1.0.zip',
              body=pkg2)
        m.get(TestArgs.murano_repo_url + '/apps/third_app.zip',
              status_code=404)

        args = TestArgs()
        args.filename = [bundle_file]
        v1_shell.do_bundle_import(self.client, args)

        self.client.packages.create.assert_has_calls(
            [
                mock.call({'is_public': False}, {'first_app': mock.ANY}),
                mock.call({'is_public': False}, {'second_app': mock.ANY}),
                mock.call({'is_public': False}, {'third_app': mock.ANY}),
            ], any_order=True,
        )
        shutil.rmtree(tmp_dir)

    @requests_mock.mock()
    def test_save_bundle(self, m):
        tmp_dir = tempfile.mkdtemp()

        pkg = make_pkg({'FullName': 'test_app'})

        expected_pkg = tempfile.NamedTemporaryFile(delete=False)
        shutil.copyfileobj(pkg, expected_pkg)
        pkg.seek(0)

        m.get(TestArgs.murano_repo_url + '/apps/test_app.zip', body=pkg)

        s = six.StringIO()
        expected_bundle = {'Packages': [
            {'Name': 'test_app'},
        ]}
        json.dump(expected_bundle, s)
        s = six.BytesIO(s.getvalue().encode('ascii'))

        m.get(TestArgs.murano_repo_url + '/bundles/test_bundle.bundle',
              body=s)

        args = TestArgs()
        args.filename = "test_bundle"
        args.path = tmp_dir

        v1_shell.do_bundle_save(self.client, args)

        expected_pkg.seek(0)
        result_bundle = json.load(open(os.path.join(
            tmp_dir, 'test_bundle.bundle')))
        result_pkg = os.path.join(tmp_dir, 'test_app.zip')

        self.assertEqual(expected_bundle, result_bundle)
        self.assertTrue(filecmp.cmp(expected_pkg.name, result_pkg))

        os.remove(expected_pkg.name)
        shutil.rmtree(tmp_dir)

    @requests_mock.mock()
    def test_package_save(self, m):
        args = TestArgs()
        tmp_dir = tempfile.mkdtemp()

        args.package = ["test_app1", "http://127.0.0.1/test_app2.zip"]
        args.path = tmp_dir

        pkgs = [
            make_pkg(
                {'FullName': 'test_app1', 'Require': {'test_app3': '1.0'}}),
            make_pkg({'FullName': 'test_app2'}),
            make_pkg({'FullName': 'test_app3'})
        ]

        m.get(TestArgs.murano_repo_url + '/apps/' + args.package[0] + '.zip',
              body=pkgs[0])
        m.get(args.package[1], body=pkgs[1])
        m.get(TestArgs.murano_repo_url + '/apps/' + 'test_app3.1.0.zip',
              body=pkgs[2])

        expected_pkgs = []

        for i in range(0, 3):
            expected_pkgs.append(tempfile.NamedTemporaryFile(delete=False))
            shutil.copyfileobj(pkgs[i], expected_pkgs[i])
            pkgs[i].seek(0)

        v1_shell.do_package_save(self.client, args)

        file_names = ['test_app1.zip', 'test_app2.zip', 'test_app3.1.0.zip']

        for i in range(0, 3):
            expected_pkgs[i].seek(0)
            result_pkg = os.path.join(tmp_dir, file_names[i])
            self.assertTrue(filecmp.cmp(expected_pkgs[i].name, result_pkg))
            os.remove(expected_pkgs[i].name)

        shutil.rmtree(tmp_dir)


class ShellPackagesOperationsV3(ShellPackagesOperations):
    def make_env(self, exclude=None, fake_env=FAKE_ENV):
        if 'OS_AUTH_URL' in fake_env:
            fake_env.update({'OS_AUTH_URL': 'http://no.where/v3'})
        env = dict((k, v) for k, v in fake_env.items() if k != exclude)
        self.useFixture(fixtures.MonkeyPatch('os.environ', env))

    def register_keystone_discovery_fixture(self, mreq):
        v3_url = "http://no.where/v3"
        v3_version = fixture.V3Discovery(v3_url)
        mreq.register_uri('GET', v3_url, json=_create_ver_list([v3_version]),
                          status_code=200)

    def register_keystone_token_fixture(self, mreq):
        v3_token = ks_v3_fixture.Token()
        service = v3_token.add_service('application-catalog')
        service.add_standard_endpoints(public='http://no.where')
        mreq.register_uri('POST',
                          'http://no.where/v3/auth/tokens',
                          json=v3_token,
                          headers={'X-Subject-Token': 'tokenid'},
                          status_code=200)
