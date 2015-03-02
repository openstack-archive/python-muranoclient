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
import logging
import sys

from keystoneclient.auth.identity.generic import password
from keystoneclient.auth.identity.generic import token
from keystoneclient.auth.identity import v3 as identity
from keystoneclient import session as ksession
from oslo.utils import encodeutils
import six

from muranoclient import client as murano_client
from muranoclient.common import utils
from muranoclient.openstack.common.apiclient import exceptions as exc


logger = logging.getLogger(__name__)


class MuranoShell(object):

    def _append_global_identity_args(self, parser):
        # Register the CLI arguments that have moved to the session object.
        ksession.Session.register_cli_options(parser)

        identity.Password.register_argparse_arguments(parser)

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

        parser.add_argument('-d', '--debug',
                            default=bool(utils.env('MURANOCLIENT_DEBUG')),
                            action='store_true',
                            help='Defaults to env[MURANOCLIENT_DEBUG]')

        parser.add_argument('-v', '--verbose',
                            default=False, action="store_true",
                            help="Print more verbose output")

        # os-cert, os-key, insecure, ca-file are all added
        # by keystone session register_cli_opts later
        parser.add_argument('--cert-file',
                            dest='os_cert',
                            help='DEPRECATED! Use --os-cert.')

        parser.add_argument('--key-file',
                            dest='os_key',
                            help='DEPRECATED! Use --os-key.')

        parser.add_argument('--ca-file',
                            dest='os_cacert',
                            help='DEPRECATED! Use --os-cacert.')

        parser.add_argument('--api-timeout',
                            help='Number of seconds to wait for an '
                                 'API response, '
                                 'defaults to system socket timeout')

        parser.add_argument('--os-tenant-id',
                            default=utils.env('OS_TENANT_ID'),
                            help='Defaults to env[OS_TENANT_ID]')

        parser.add_argument('--os-tenant-name',
                            default=utils.env('OS_TENANT_NAME'),
                            help='Defaults to env[OS_TENANT_NAME]')

        parser.add_argument('--os-region-name',
                            default=utils.env('OS_REGION_NAME'),
                            help='Defaults to env[OS_REGION_NAME]')

        parser.add_argument('--os-auth-token',
                            default=utils.env('OS_AUTH_TOKEN'),
                            help='Defaults to env[OS_AUTH_TOKEN]')

        parser.add_argument('--os-no-client-auth',
                            default=utils.env('OS_NO_CLIENT_AUTH'),
                            action='store_true',
                            help="Do not contact keystone for a token. "
                                 "Defaults to env[OS_NO_CLIENT_AUTH].")
        parser.add_argument('--murano-url',
                            default=utils.env('MURANO_URL'),
                            help='Defaults to env[MURANO_URL]')

        parser.add_argument('--murano-api-version',
                            default=utils.env(
                                'MURANO_API_VERSION', default='1'),
                            help='Defaults to env[MURANO_API_VERSION] '
                                 'or 1')

        parser.add_argument('--os-service-type',
                            default=utils.env('OS_SERVICE_TYPE'),
                            help='Defaults to env[OS_SERVICE_TYPE]')

        parser.add_argument('--os-endpoint-type',
                            default=utils.env('OS_ENDPOINT_TYPE'),
                            help='Defaults to env[OS_ENDPOINT_TYPE]')

        parser.add_argument('--include-password',
                            default=bool(utils.env('MURANO_INCLUDE_PASSWORD')),
                            action='store_true',
                            help='Send os-username and os-password to murano.')

        self._append_global_identity_args(parser)

        return parser

    def get_subcommand_parser(self, version):
        parser = self.get_base_parser()

        self.subcommands = {}
        subparsers = parser.add_subparsers(metavar='<subcommand>')
        submodule = utils.import_versioned_module(version, 'shell')
        self._find_actions(subparsers, submodule)
        self._find_actions(subparsers, self)

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

    def _get_keystone_auth(self, session, auth_url, **kwargs):
        auth_token = kwargs.pop('auth_token', None)
        if auth_token:
            return token.Token(auth_url, auth_token, **kwargs)
        else:
            user_domain_id = kwargs.pop('user_domain_id')
            user_domain_name = kwargs.pop('user_domain_name')
            return password.Password(auth_url,
                                     username=kwargs.pop('username'),
                                     user_id=kwargs.pop('user_id'),
                                     password=kwargs.pop('password'),
                                     user_domain_id=user_domain_id,
                                     user_domain_name=user_domain_name,
                                     **kwargs)

    def _setup_logging(self, debug):
        log_lvl = logging.DEBUG if debug else logging.WARNING
        logging.basicConfig(
            format="%(levelname)s (%(module)s:%(lineno)d) %(message)s",
            level=log_lvl)

    def _setup_verbose(self, verbose):
        if verbose:
            exc.verbose = 1

    def main(self, argv):
        # Parse args once to find version
        parser = self.get_base_parser()
        (options, args) = parser.parse_known_args(argv)
        self._setup_logging(options.debug)
        self._setup_verbose(options.verbose)

        # build available subcommands based on version
        api_version = options.murano_api_version
        subcommand_parser = self.get_subcommand_parser(api_version)
        self.parser = subcommand_parser

        keystone_session = None
        keystone_auth = None

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

        if not any([args.os_tenant_name, args.os_tenant_id,
                    args.os_project_id, args.os_project_name]):
            raise exc.CommandError("You must provide a project name or"
                                   " project id via --os-project-name,"
                                   " --os-project-id, env[OS_PROJECT_ID]"
                                   " or env[OS_PROJECT_NAME]. You may"
                                   " use os-project and os-tenant"
                                   " interchangeably.")

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
                raise exc.CommandError(
                    "You must provide a tenant name "
                    "or tenant id via --os-tenant-name, "
                    "--os-tenant-id, env[OS_TENANT_NAME] "
                    "or env[OS_TENANT_ID] OR a project name "
                    "or project id via --os-project-name, "
                    "--os-project-id, env[OS_PROJECT_ID] or "
                    "env[OS_PROJECT_NAME]")

            if not args.os_auth_url:
                raise exc.CommandError("You must provide an auth url via"
                                       " either --os-auth-url or via"
                                       " env[OS_AUTH_URL]")

        endpoint = args.murano_url

        if args.os_no_client_auth:
            # Authenticate through murano, don't use session
            kwargs = {
                'username': args.os_username,
                'password': args.os_password,
                'auth_token': args.os_auth_token,
                'auth_url': args.os_auth_url,
                'token': args.os_auth_token,
                'insecure': args.insecure,
                'timeout': args.api_timeout
            }
        else:
            # Create a keystone session and keystone auth
            keystone_session = ksession.Session.load_from_cli_options(args)
            project_id = args.os_project_id or args.os_tenant_id
            project_name = args.os_project_name or args.os_tenant_name

            keystone_session = ksession.Session.load_from_cli_options(args)

            keystone_auth = self._get_keystone_auth(
                keystone_session,
                args.os_auth_url,
                username=args.os_username,
                user_id=args.os_user_id,
                user_domain_id=args.os_user_domain_id,
                user_domain_name=args.os_user_domain_name,
                password=args.os_password,
                auth_token=args.os_auth_token,
                project_id=project_id,
                project_name=project_name,
                project_domain_id=args.os_project_domain_id,
                project_domain_name=args.os_project_domain_name)

            endpoint_type = args.os_endpoint_type or 'publicURL'
            service_type = args.os_service_type or 'application_catalog'

            if not endpoint:
                endpoint = keystone_auth.get_endpoint(
                    keystone_session,
                    service_type=service_type,
                    region_name=args.os_region_name)

            kwargs = {
                'session': keystone_session,
                'auth': keystone_auth,
                'service_type': service_type,
                'endpoint_type': endpoint_type,
                'region_name': args.os_region_name,
            }

        if args.api_timeout:
            kwargs['timeout'] = args.api_timeout

        client = murano_client.Client(api_version, endpoint, **kwargs)

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
