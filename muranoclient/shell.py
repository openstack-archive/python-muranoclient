#    Copyright (c) 2013 Mirantis, Inc.
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

"""
Command-line interface to the Murano Project.
"""

from __future__ import print_function

import argparse
import sys

import glanceclient
from keystoneclient.v2_0 import client as ksclient
from oslo_log import handlers
from oslo_log import log as logging
from oslo_utils import encodeutils
import six

import muranoclient
from muranoclient import client as apiclient
from muranoclient.common import utils
from muranoclient.openstack.common.apiclient import exceptions as exc
from muranoclient.openstack.common.gettextutils import _


logger = logging.getLogger(__name__)

DEFAULT_REPO_URL = "http://apps.openstack.org/api/v1/murano_repo/liberty/"


class MuranoShell(object):
    def get_base_parser(self):
        parser = argparse.ArgumentParser(
            prog='murano',
            description=__doc__.strip(),
            epilog='See "murano help COMMAND" '
                   'for help on a specific command.',
            add_help=False,
            formatter_class=HelpFormatter,
        )

        # Global arguments
        parser.add_argument('-h', '--help',
                            action='store_true',
                            help=argparse.SUPPRESS,)

        parser.add_argument('--version',
                            action='version',
                            version=muranoclient.__version__,
                            help="Show program's version number and exit.")

        parser.add_argument('-d', '--debug',
                            default=bool(utils.env('MURANOCLIENT_DEBUG')),
                            action='store_true',
                            help='Defaults to env[MURANOCLIENT_DEBUG].')

        parser.add_argument('-v', '--verbose',
                            default=False, action="store_true",
                            help="Print more verbose output.")

        parser.add_argument('-k', '--insecure',
                            default=False,
                            action='store_true',
                            help="Explicitly allow muranoclient to perform "
                                 "\"insecure\" SSL (https) requests. "
                                 "The server's certificate will "
                                 "not be verified against any certificate "
                                 "authorities. This option should be used "
                                 "with caution.")

        parser.add_argument('--os-cacert',
                            metavar='<ca-certificate>',
                            default=utils.env('OS_CACERT', default=None),
                            dest='os_cacert',
                            help='Specify a CA bundle file to use in '
                                 'verifying a TLS (https) server certificate. '
                                 'Defaults to env[OS_CACERT].')

        parser.add_argument('--cert-file',
                            help='Path of certificate file to use in SSL '
                                 'connection. This file can optionally be '
                                 'prepended with the private key.')

        parser.add_argument('--key-file',
                            help='Path of client key to use '
                                 'in SSL connection. This option '
                                 'is not necessary if your key '
                                 'is prepended to your cert file.')

        parser.add_argument('--ca-file',
                            dest='os_cacert',
                            help=_('DEPRECATED! Use %(arg)s.') %
                                 {'arg': '--os-cacert'})

        parser.add_argument('--api-timeout',
                            help='Number of seconds to wait for an '
                                 'API response, '
                                 'defaults to system socket timeout.')

        parser.add_argument('--os-username',
                            default=utils.env('OS_USERNAME'),
                            help='Defaults to env[OS_USERNAME].')

        parser.add_argument('--os-password',
                            default=utils.env('OS_PASSWORD'),
                            help='Defaults to env[OS_PASSWORD].')

        parser.add_argument('--os-tenant-id',
                            default=utils.env('OS_TENANT_ID'),
                            help='Defaults to env[OS_TENANT_ID].')

        parser.add_argument('--os-tenant-name',
                            default=utils.env('OS_TENANT_NAME'),
                            help='Defaults to env[OS_TENANT_NAME].')

        parser.add_argument('--os-auth-url',
                            default=utils.env('OS_AUTH_URL'),
                            help='Defaults to env[OS_AUTH_URL].')

        parser.add_argument('--os-region-name',
                            default=utils.env('OS_REGION_NAME'),
                            help='Defaults to env[OS_REGION_NAME].')

        parser.add_argument('--os-auth-token',
                            default=utils.env('OS_AUTH_TOKEN'),
                            help='Defaults to env[OS_AUTH_TOKEN].')

        parser.add_argument('--os-no-client-auth',
                            default=utils.env('OS_NO_CLIENT_AUTH'),
                            action='store_true',
                            help="Do not contact keystone for a token. "
                                 "Defaults to env[OS_NO_CLIENT_AUTH].")

        parser.add_argument('--murano-url',
                            default=utils.env('MURANO_URL'),
                            help='Defaults to env[MURANO_URL].')

        parser.add_argument('--glance-url',
                            default=utils.env('GLANCE_URL'),
                            help='Defaults to env[GLANCE_URL].')

        parser.add_argument('--murano-api-version',
                            default=utils.env(
                                'MURANO_API_VERSION', default='1'),
                            help='Defaults to env[MURANO_API_VERSION] '
                                 'or 1.')

        parser.add_argument('--os-service-type',
                            default=utils.env('OS_SERVICE_TYPE'),
                            help='Defaults to env[OS_SERVICE_TYPE].')

        parser.add_argument('--os-endpoint-type',
                            default=utils.env('OS_ENDPOINT_TYPE'),
                            help='Defaults to env[OS_ENDPOINT_TYPE].')

        parser.add_argument('--include-password',
                            default=bool(utils.env('MURANO_INCLUDE_PASSWORD')),
                            action='store_true',
                            help='Send os-username and os-password to murano.')

        parser.add_argument('--murano-repo-url',
                            default=utils.env(
                                'MURANO_REPO_URL',
                                default=DEFAULT_REPO_URL),
                            help=('Defaults to env[MURANO_REPO_URL] '
                                  'or {0}'.format(DEFAULT_REPO_URL)))

        return parser

    def get_subcommand_parser(self, version):
        parser = self.get_base_parser()

        self.subcommands = {}
        subparsers = parser.add_subparsers(metavar='<subcommand>')
        submodule = utils.import_versioned_module(version, 'shell')
        self._find_actions(subparsers, submodule)
        self._find_actions(subparsers, self)

        self._add_bash_completion_subparser(subparsers)

        return parser

    def _add_bash_completion_subparser(self, subparsers):
        subparser = subparsers.add_parser(
            'bash_completion',
            add_help=False,
            formatter_class=HelpFormatter
        )
        self.subcommands['bash_completion'] = subparser
        subparser.set_defaults(func=self.do_bash_completion)

    def _find_actions(self, subparsers, actions_module):
        for attr in (a for a in dir(actions_module) if a.startswith('do_')):
            # I prefer to be hypen-separated instead of underscores.
            command = attr[3:].replace('_', '-')
            callback = getattr(actions_module, attr)
            desc = callback.__doc__ or ''
            help = desc.strip().split('\n')[0]
            arguments = getattr(callback, 'arguments', [])

            subparser = subparsers.add_parser(command, help=help,
                                              description=desc,
                                              add_help=False,
                                              formatter_class=HelpFormatter)
            subparser.add_argument('-h', '--help', action='help',
                                   help=argparse.SUPPRESS)
            self.subcommands[command] = subparser
            for (args, kwargs) in arguments:
                subparser.add_argument(*args, **kwargs)
            subparser.set_defaults(func=callback)

    def _get_ksclient(self, **kwargs):
        """Get an endpoint and auth token from Keystone.

        :param username: name of user
        :param password: user's password
        :param tenant_id: unique identifier of tenant
        :param tenant_name: name of tenant
        :param auth_url: endpoint to authenticate against
        """
        kc_args = {
            'auth_url': kwargs.get('auth_url'),
            'insecure': kwargs.get('insecure'),
            'cacert': kwargs.get('cacert')}

        if kwargs.get('tenant_id'):
            kc_args['tenant_id'] = kwargs.get('tenant_id')
        else:
            kc_args['tenant_name'] = kwargs.get('tenant_name')

        if kwargs.get('token'):
            kc_args['token'] = kwargs.get('token')
        else:
            kc_args['username'] = kwargs.get('username')
            kc_args['password'] = kwargs.get('password')

        return ksclient.Client(**kc_args)

    def _get_endpoint(self, client, **kwargs):
        """Get an endpoint using the provided keystone client."""
        return client.service_catalog.url_for(
            service_type=kwargs.get('service_type') or 'application_catalog',
            endpoint_type=kwargs.get('endpoint_type') or 'publicURL')

    def _setup_logging(self, debug):
        # Output the logs to command-line interface
        color_handler = handlers.ColorHandler(sys.stdout)
        logger_root = logging.getLogger(None).logger
        logger_root.level = logging.DEBUG if debug else logging.WARNING
        logger_root.addHandler(color_handler)

        # Set the logger level of special library
        logging.getLogger('iso8601') \
               .logger.setLevel(logging.WARNING)
        logging.getLogger('urllib3.connectionpool') \
               .logger.setLevel(logging.WARNING)

    def main(self, argv):
        # Parse args once to find version
        parser = self.get_base_parser()
        (options, args) = parser.parse_known_args(argv)
        self._setup_logging(options.debug)

        # build available subcommands based on version
        api_version = options.murano_api_version
        subcommand_parser = self.get_subcommand_parser(api_version)
        self.parser = subcommand_parser

        # Handle top-level --help/-h before attempting to parse
        # a command off the command line.
        if (not args and options.help) or not argv:
            self.do_help(options)
            return 0

        # Parse args again and call whatever callback was selected.
        args = subcommand_parser.parse_args(argv)

        # Short-circuit and deal with help command right away.
        if args.func == self.do_help:
            self.do_help(args)
            return 0
        elif args.func == self.do_bash_completion:
            self.do_bash_completion(args)
            return 0

        if not args.os_username and not args.os_auth_token:
            raise exc.CommandError("You must provide a username via"
                                   " either --os-username or env[OS_USERNAME]"
                                   " or a token via --os-auth-token or"
                                   " env[OS_AUTH_TOKEN]")

        if not args.os_password and not args.os_auth_token:
            raise exc.CommandError("You must provide a password via"
                                   " either --os-password or env[OS_PASSWORD]"
                                   " or a token via --os-auth-token or"
                                   " env[OS_AUTH_TOKEN]")

        if args.os_no_client_auth:
            if not args.murano_url:
                raise exc.CommandError(
                    "If you specify --os-no-client-auth"
                    " you must also specify a Murano API URL"
                    " via either --murano-url or env[MURANO_URL]")
        else:
            # Tenant name or ID is needed to make keystoneclient retrieve a
            # service catalog, it's not required if os_no_client_auth is
            # specified, neither is the auth URL.
            if not (args.os_tenant_id or args.os_tenant_name):
                raise exc.CommandError("You must provide a tenant name "
                                       "or tenant id via --os-tenant-name, "
                                       "--os-tenant-id, env[OS_TENANT_NAME] "
                                       "or env[OS_TENANT_ID]")

            if not args.os_auth_url:
                raise exc.CommandError("You must provide an auth url via"
                                       " either --os-auth-url or via"
                                       " env[OS_AUTH_URL]")

        kwargs = {
            'username': args.os_username,
            'password': args.os_password,
            'token': args.os_auth_token,
            'tenant_id': args.os_tenant_id,
            'tenant_name': args.os_tenant_name,
            'auth_url': args.os_auth_url,
            'service_type': args.os_service_type,
            'endpoint_type': args.os_endpoint_type,
            'insecure': args.insecure,
            'cacert': args.os_cacert,
            'include_pass': args.include_password
        }
        glance_kwargs = kwargs
        glance_kwargs = kwargs.copy()

        endpoint = args.murano_url
        glance_endpoint = args.glance_url

        if not args.os_no_client_auth:
            _ksclient = self._get_ksclient(**kwargs)
            token = args.os_auth_token or _ksclient.auth_token

            kwargs = {
                'token': token,
                'insecure': args.insecure,
                'cacert': args.os_cacert,
                'cert_file': args.cert_file,
                'key_file': args.key_file,
                'username': args.os_username,
                'password': args.os_password,
                'endpoint_type': args.os_endpoint_type,
                'include_pass': args.include_password
            }
            glance_kwargs = kwargs.copy()

            if args.os_region_name:
                kwargs['region_name'] = args.os_region_name
                glance_kwargs['region_name'] = args.os_region_name

            if not endpoint:
                endpoint = self._get_endpoint(_ksclient, **kwargs)

        if args.api_timeout:
            kwargs['timeout'] = args.api_timeout

        if not glance_endpoint:
            try:
                glance_endpoint = self._get_endpoint(
                    _ksclient, service_type='image')
            except Exception:
                pass

        glance_client = None
        if glance_endpoint:
            try:
                glance_client = glanceclient.Client(
                    '1', glance_endpoint, **glance_kwargs)
            except Exception:
                pass
        if glance_client:
            kwargs['glance_client'] = glance_client
        else:
            logger.warning("Could not initialise glance client. "
                           "Image creation will be unavailable.")
            kwargs['glance_client'] = None

        client = apiclient.Client(api_version, endpoint, **kwargs)

        args.func(client, args)

    def do_bash_completion(self, args):
        """Prints all of the commands and options to stdout."""
        commands = set()
        options = set()
        for sc_str, sc in self.subcommands.items():
            commands.add(sc_str)
            for option in list(sc._optionals._option_string_actions):
                options.add(option)

        commands.remove('bash-completion')
        commands.remove('bash_completion')
        print(' '.join(commands | options))

    @utils.arg('command', metavar='<subcommand>', nargs='?',
               help='Display help for <subcommand>')
    def do_help(self, args):
        """Display help about this program or one of its subcommands.
        """
        if getattr(args, 'command', None):
            if args.command in self.subcommands:
                self.subcommands[args.command].print_help()
            else:
                msg = "'%s' is not a valid subcommand"
                raise exc.CommandError(msg % args.command)
        else:
            self.parser.print_help()


class HelpFormatter(argparse.HelpFormatter):
    def start_section(self, heading):
        # Title-case the headings
        heading = '%s%s' % (heading[0].upper(), heading[1:])
        super(HelpFormatter, self).start_section(heading)


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    try:
        MuranoShell().main(args)

    except KeyboardInterrupt:
        print('... terminating murano client', file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        if '--debug' in args or '-d' in args:
            raise
        else:
            print(encodeutils.safe_encode(six.text_type(e)), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
