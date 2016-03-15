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

"""Application-catalog v1 stack action implementation"""

from cliff import lister
from cliff import show
from muranoclient.common import utils as murano_utils
from openstackclient.common import utils
from oslo_log import log as logging
from oslo_serialization import jsonutils


class ListEnvironments(lister.Lister):
    """Lists environments"""

    log = logging.getLogger(__name__ + ".ListEnvironments")

    def get_parser(self, prog_name):
        parser = super(ListEnvironments, self).get_parser(prog_name)
        parser.add_argument(
            '--all-tenants',
            action='store_true',
            default=False,
            help='List environments from all tenants (admin only).',
        )

        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action({0})".format(parsed_args))
        client = self.app.client_manager.application_catalog
        data = client.environments.list(parsed_args.all_tenants)

        columns = ('id', 'name', 'created', 'updated')
        column_headers = [c.capitalize() for c in columns]

        return (
            column_headers,
            list(utils.get_item_properties(
                s,
                columns,
            ) for s in data)
        )


class ShowEnvironment(show.ShowOne):
    """Display environment details"""

    log = logging.getLogger(__name__ + ".ShowEnvironment")

    def get_parser(self, prog_name):
        parser = super(ShowEnvironment, self).get_parser(prog_name)
        parser.add_argument(
            "id",
            metavar="<NAME or ID>",
            help=("Name or ID of the environment to display"),
        )
        parser.add_argument(
            "--only-apps",
            action='store_true',
            default=False,
            help="Only print apps of the environment (useful for automation).",
        )
        parser.add_argument(
            "--session-id",
            metavar="<SESSION_ID>",
            default='',
            help="Id of a config session.",
        )

        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action({0})".format(parsed_args))
        client = self.app.client_manager.application_catalog

        environment = utils.find_resource(client.environments,
                                          parsed_args.id)
        data = client.environments.get(environment.id,
                                       parsed_args.session_id).to_dict()

        data['services'] = jsonutils.dumps(data['services'], indent=2)

        if getattr(parsed_args, 'only_apps', False):
            return(['services'], [data['services']])
        else:
            return self.dict2columns(data)


class RenameEnvironment(lister.Lister):
    """Rename an environment."""

    log = logging.getLogger(__name__ + ".RenameEnvironment")

    def get_parser(self, prog_name):
        parser = super(RenameEnvironment, self).get_parser(prog_name)
        parser.add_argument(
            'id',
            metavar="<NAME or ID>",
            help="Environment ID or name.",
        )
        parser.add_argument(
            'name',
            metavar="<ENVIRONMENT_NAME>",
            help="A name to which the environment will be renamed.",
        )

        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action({0})".format(parsed_args))
        client = self.app.client_manager.application_catalog
        environment = utils.find_resource(client.environments,
                                          parsed_args.id)
        data = client.environments.update(environment.id,
                                          parsed_args.name)

        columns = ('id', 'name', 'created', 'updated')
        column_headers = [c.capitalize() for c in columns]

        return (
            column_headers,
            [utils.get_item_properties(
                data,
                columns,
            )]
        )


class EnvironmentSessionCreate(show.ShowOne):
    """Creates a new configuration session for environment ID."""

    log = logging.getLogger(__name__ + ".EnvironmentSessionCreate")

    def get_parser(self, prog_name):
        parser = super(EnvironmentSessionCreate, self).get_parser(prog_name)
        parser.add_argument(
            'id',
            metavar="<ID>",
            help="ID of Environment to add session to.",
        )

        return parser

    def take_action(self, parsed_args):
        self.log.debug("take_action({0})".format(parsed_args))
        client = self.app.client_manager.application_catalog

        environment_id = parsed_args.id
        session_id = client.sessions.configure(environment_id).id
        sessionid = murano_utils.text_wrap_formatter(session_id)

        return (['id'], [sessionid])
