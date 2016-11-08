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

"""Application-catalog v1 action implementation"""

import json

from osc_lib.command import command
from oslo_log import log as logging

from muranoclient.apiclient import exceptions

LOG = logging.getLogger(__name__)


class StaticActionCall(command.ShowOne):
    """Call static method of the MuranoPL class."""

    def get_parser(self, prog_name):
        parser = super(StaticActionCall, self).get_parser(prog_name)
        parser.add_argument(
            "class_name",
            metavar='<CLASS>',
            help="FQN of the class with static method",
        )
        parser.add_argument(
            "method_name",
            metavar='<METHOD>',
            help="Static method to run",
        )
        parser.add_argument(
            "--arguments",
            metavar='<KEY=VALUE>',
            nargs='*',
            help="Method arguments. No arguments by default",
        )
        parser.add_argument(
            "--package-name",
            metavar='<PACKAGE>',
            default='',
            help='Optional FQN of the package to look for the class in',
        )
        parser.add_argument(
            "--class-version",
            default='',
            help='Optional version of the class, otherwise version =0 is '
                 'used ',
        )

        return parser

    def take_action(self, parsed_args):
        LOG.debug("take_action({0})".format(parsed_args))
        client = self.app.client_manager.application_catalog

        arguments = {}
        for argument in parsed_args.arguments or []:
            if '=' not in argument:
                raise exceptions.CommandError(
                    "Argument should be in form of KEY=VALUE. Found: "
                    "{0}".format(argument))
            key, value = argument.split('=', 1)
            try:
                value = json.loads(value)
            except ValueError:
                # treat value as a string if it doesn't load as json
                pass

            arguments[key] = value

        request_body = {
            "className": parsed_args.class_name,
            "methodName": parsed_args.method_name,
            "packageName": parsed_args.package_name or None,
            "classVersion": parsed_args.class_version or '=0',
            "parameters": arguments
        }

        print("Waiting for result...")
        result = client.static_actions.call(request_body).get_result()
        return ["Static action result"], [result]
