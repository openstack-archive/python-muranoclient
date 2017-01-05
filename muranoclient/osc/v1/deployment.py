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

"""Application-catalog v1 deployments action implementation"""

from osc_lib.command import command
from osc_lib import utils
from oslo_log import log as logging

from muranoclient.apiclient import exceptions

LOG = logging.getLogger(__name__)


class ListDeployment(command.Lister):
    """List deployments for an environment."""

    def get_parser(self, prog_name):
        parser = super(ListDeployment, self).get_parser(prog_name)
        parser.add_argument(
            "id",
            metavar="<ID>",
            nargs="?",
            default=None,
            help=("Environment ID for which to list deployments."),
        )
        parser.add_argument(
            "--all-environments",
            action="store_true",
            default=False,
            help="List all deployments for all environments in user's tenant."
        )

        return parser

    def take_action(self, parsed_args):
        LOG.debug("take_action({0})".format(parsed_args))
        client = self.app.client_manager.application_catalog

        all_environments = getattr(parsed_args, 'all_environments', False)
        env_id = getattr(parsed_args, 'id', None)

        if env_id and all_environments:
            raise exceptions.CommandError(
                'Environment ID and all-environments flag cannot both be set.')
        elif not env_id and not all_environments:
            raise exceptions.CommandError(
                'Either environment ID or all-environments flag must be set.')

        if all_environments:
            data = client.deployments.list(None, all_environments)
        else:
            environment = utils.find_resource(client.environments,
                                              env_id)
            data = client.deployments.list(environment.id)

        columns = ('id', 'state', 'created', 'updated', 'finished')
        column_headers = [c.capitalize() for c in columns]
        return (
            column_headers,
            list(utils.get_item_properties(
                s,
                columns,
            ) for s in data)
        )
