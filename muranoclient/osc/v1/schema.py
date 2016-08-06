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

"""Application-catalog v1 class-schema action implementation"""

from osc_lib.command import command
from oslo_log import log as logging

LOG = logging.getLogger(__name__)


class ShowSchema(command.ShowOne):
    """Show class schema."""

    def get_parser(self, prog_name):
        parser = super(ShowSchema, self).get_parser(prog_name)
        parser.add_argument(
            "class_name", metavar="<CLASS>", help="Class FQN")
        parser.add_argument(
            "method_names", metavar="<METHOD>",
            help="Method name", nargs='*')
        parser.add_argument(
            "--package-name", default=None,
            help="FQN of the package where the class is located")
        parser.add_argument(
            "--class-version", default='=0',
            help="Class version or version range (version spec)")

        return parser

    def take_action(self, parsed_args):
        LOG.debug("take_action({0})".format(parsed_args))
        client = self.app.client_manager.application_catalog
        schema = client.schemas.get(
            parsed_args.class_name, parsed_args.method_names,
            class_version=parsed_args.class_version,
            package_name=parsed_args.package_name)

        return self.dict2columns(schema.data)

    @property
    def formatter_default(self):
        return 'json'
