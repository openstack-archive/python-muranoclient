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

LOG = logging.getLogger(__name__)


class ListDeployment(command.Lister):
    """List deployments for an environment."""

    def get_parser(self, prog_name):
        parser = super(ListDeployment, self).get_parser(prog_name)
        parser.add_argument(
            "id",
            metavar="<ID>",
            help=("Environment ID for which to list deployments."),
        )

        return parser

    def take_action(self, parsed_args):
        LOG.debug("take_action({0})".format(parsed_args))
        client = self.app.client_manager.application_catalog

        environment = utils.find_resource(client.environments,
                                          parsed_args.id)
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
