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

"""Application-catalog v1 category action implementation"""

import textwrap

from muranoclient.openstack.common.apiclient import exceptions
from osc_lib.command import command
from osc_lib import utils
from oslo_log import log as logging

LOG = logging.getLogger(__name__)


class ListCategories(command.Lister):
    """List all available categories."""

    def take_action(self, parsed_args=None):
        LOG.debug("take_action({0})".format(parsed_args))
        client = self.app.client_manager.application_catalog

        if parsed_args is None:
            parsed_args = {}

        data = client.categories.list()

        fields = ["id", "name"]
        field_labels = ["ID", "Name"]

        return (
            field_labels,
            list(utils.get_item_properties(
                s,
                fields,
            ) for s in data)
        )


class ShowCategory(command.ShowOne):
    """Display category details."""

    def get_parser(self, prog_name):
        parser = super(ShowCategory, self).get_parser(prog_name)
        parser.add_argument(
            "id",
            metavar="<ID>",
            help=("ID of a category(s) to show."),
        )

        return parser

    def take_action(self, parsed_args):
        LOG.debug("take_action({0})".format(parsed_args))
        client = self.app.client_manager.application_catalog

        category = client.categories.get(parsed_args.id)
        packages = client.packages.filter(category=category.name)
        to_display = dict(id=category.id,
                          name=category.name,
                          packages=', '.join(p.name
                                             for p in packages))

        to_display['packages'] = '\n'.join(textwrap.wrap(to_display['packages']
                                           or '', 55))

        return self.dict2columns(to_display)


class CreateCategory(command.Lister):
    """Create a category."""

    def get_parser(self, prog_name):
        parser = super(CreateCategory, self).get_parser(prog_name)
        parser.add_argument(
            "name",
            metavar="<CATEGORY_NAME>",
            help=("Category name."),
        )

        return parser

    def take_action(self, parsed_args):
        LOG.debug("take_action({0})".format(parsed_args))
        client = self.app.client_manager.application_catalog

        data = [client.categories.add({"name": parsed_args.name})]

        fields = ["id", "name"]
        field_labels = ["ID", "Name"]

        return (
            field_labels,
            list(utils.get_item_properties(
                s,
                fields,
            ) for s in data)
        )


class DeleteCategory(command.Lister):
    """Delete a category."""

    def get_parser(self, prog_name):
        parser = super(DeleteCategory, self).get_parser(prog_name)
        parser.add_argument(
            "id",
            metavar="<ID>",
            nargs="+",
            help=("ID of a category(ies) to delete."),
        )

        return parser

    def take_action(self, parsed_args):
        LOG.debug("take_action({0})".format(parsed_args))
        client = self.app.client_manager.application_catalog

        failure_count = 0
        for category_id in parsed_args.id:
            try:
                client.categories.delete(category_id)
            except Exception:
                failure_count += 1
                print("Failed to delete '{0}'; category not found".
                      format(category_id))
        if failure_count == len(parsed_args.id):
            raise exceptions.CommandError("Unable to find and delete any of "
                                          "the specified categories.")
        data = client.categories.list()

        fields = ["id", "name"]
        field_labels = ["ID", "Name"]

        return (
            field_labels,
            list(utils.get_item_properties(
                s,
                fields,
            ) for s in data)
        )
