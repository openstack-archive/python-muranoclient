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

"""Application-catalog v1 package action implementation"""

import itertools
import os
import shutil
import tempfile
import zipfile

from osc_lib.command import command
from osc_lib import exceptions as exc
from osc_lib import utils
from oslo_log import log as logging

from muranoclient.apiclient import exceptions
from muranoclient.v1.package_creator import hot_package
from muranoclient.v1.package_creator import mpl_package


LOG = logging.getLogger(__name__)


class CreatePackage(command.Command):
    """Create an application package."""

    def get_parser(self, prog_name):
        parser = super(CreatePackage, self).get_parser(prog_name)
        parser.add_argument(
            '-t', '--template',
            metavar='<HEAT_TEMPLATE>',
            help=("Path to the Heat template to import as "
                  "an Application Definition."),
        )
        parser.add_argument(
            '-c', '--classes-dir',
            metavar='<CLASSES_DIRECTORY>',
            help=("Path to the directory containing application classes."),
        )
        parser.add_argument(
            '-r', '--resources-dir',
            metavar='<RESOURCES_DIRECTORY>',
            help=("Path to the directory containing application resources."),
        )
        parser.add_argument(
            '-n', '--name',
            metavar='<DISPLAY_NAME>',
            help=("Display name of the Application in Catalog."),
        )
        parser.add_argument(
            '-f', '--full-name',
            metavar='<full-name>',
            help=("Fully-qualified name of the Application in Catalog."),
        )
        parser.add_argument(
            '-a', '--author',
            metavar='<AUTHOR>',
            help=("Name of the publisher."),
        )
        parser.add_argument(
            '--tags',
            metavar='<TAG1 TAG2>',
            nargs='*',
            help=("A list of keywords connected to the application."),
        )
        parser.add_argument(
            '-d', '--description',
            metavar='<DESCRIPTION>',
            help=("Detailed description for the Application in Catalog."),
        )
        parser.add_argument(
            '-o', '--output',
            metavar='<PACKAGE_NAME>',
            help=("The name of the output file archive to save locally."),
        )
        parser.add_argument(
            '-u', '--ui',
            metavar='<UI_DEFINITION>',
            help=("Dynamic UI form definition."),
        )
        parser.add_argument(
            '--type',
            metavar='<TYPE>',
            help=("Package type. Possible values: Application or Library."),
        )
        parser.add_argument(
            '-l', '--logo',
            metavar='<LOGO>',
            help=("Path to the package logo."),
        )

        return parser

    def take_action(self, parsed_args):
        LOG.debug("take_action({0})".format(parsed_args))
        parsed_args.os_username = os.getenv('OS_USERNAME')

        def _make_archive(archive_name, path):
            zip_file = zipfile.ZipFile(archive_name, 'w')
            for root, dirs, files in os.walk(path):
                for f in files:
                    zip_file.write(os.path.join(root, f),
                                   arcname=os.path.join(
                                   os.path.relpath(root, path), f))

        if parsed_args.template and parsed_args.classes_dir:
            raise exc.CommandError(
                "Provide --template for a HOT-based package, OR"
                " --classes-dir for a MuranoPL-based package")
        if not parsed_args.template and not parsed_args.classes_dir:
            raise exc.CommandError(
                "Provide --template for a HOT-based package, OR at least"
                " --classes-dir for a MuranoPL-based package")
        directory_path = None
        try:
            archive_name = parsed_args.output if parsed_args.output else None
            if parsed_args.template:
                directory_path = hot_package.prepare_package(parsed_args)
                if not archive_name:
                    archive_name = os.path.basename(parsed_args.template)
                    archive_name = os.path.splitext(archive_name)[0] + ".zip"
            else:
                directory_path = mpl_package.prepare_package(parsed_args)
                if not archive_name:
                    archive_name = tempfile.mkstemp(
                        prefix="murano_", dir=os.getcwd())[1] + ".zip"

            _make_archive(archive_name, directory_path)
            print("Application package is available at " +
                  os.path.abspath(archive_name))
        finally:
            if directory_path:
                shutil.rmtree(directory_path)


class ListPackages(command.Lister):
    """List available packages."""

    def get_parser(self, prog_name):
        parser = super(ListPackages, self).get_parser(prog_name)
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help='Show limited number of packages'
        )
        parser.add_argument(
            "--marker",
            default='',
            help='Show packages starting from package with id excluding it'
        )
        parser.add_argument(
            "--include-disabled",
            default=False,
            action="store_true"
        )
        parser.add_argument(
            "--owned",
            default=False,
            action="store_true"
        )
        parser.add_argument(
            '--search',
            metavar='<SEARCH_KEYS>',
            dest='search',
            required=False,
            help='Show packages, that match search keys fuzzily'
        )
        parser.add_argument(
            '--name',
            metavar='<PACKAGE_NAME>',
            dest='name',
            required=False,
            help='Show packages, whose name match parameter exactly'
        )
        parser.add_argument(
            '--fqn',
            metavar="<PACKAGE_FULLY_QUALIFIED_NAME>",
            dest='fqn',
            required=False,
            help='Show packages, '
                 'whose fully qualified name match parameter exactly'
        )
        parser.add_argument(
            '--type',
            metavar='<PACKAGE_TYPE>',
            dest='type',
            required=False,
            help='Show packages, whose type match parameter exactly'
        )
        parser.add_argument(
            '--category',
            metavar='<PACKAGE_CATEGORY>',
            dest='category',
            required=False,
            help='Show packages, whose categories include parameter'
        )
        parser.add_argument(
            '--class_name',
            metavar='<PACKAGE_CLASS_NAME>',
            dest='class_name',
            required=False,
            help='Show packages, whose class name match parameter exactly'
        )
        parser.add_argument(
            '--tag',
            metavar='<PACKAGE_TAG>',
            dest='tag',
            required=False,
            help='Show packages, whose tags include parameter'
        )

        return parser

    def take_action(self, parsed_args):
        LOG.debug("take_action({0})".format(parsed_args))
        client = self.app.client_manager.application_catalog
        filter_args = {
            "include_disabled": getattr(parsed_args,
                                        'include_disabled', False),
            "owned": getattr(parsed_args, 'owned', False),
        }
        if parsed_args:
            if parsed_args.limit < 0:
                raise exceptions.CommandError(
                    '--limit parameter must be non-negative')
            if parsed_args.limit != 0:
                filter_args['limit'] = parsed_args.limit
            if parsed_args.marker:
                filter_args['marker'] = parsed_args.marker
            if parsed_args.search:
                filter_args['search'] = parsed_args.search
            if parsed_args.name:
                filter_args['name'] = parsed_args.name
            if parsed_args.fqn:
                filter_args['fqn'] = parsed_args.fqn
            if parsed_args.type:
                filter_args['type'] = parsed_args.type
            if parsed_args.category:
                filter_args['category'] = parsed_args.category
            if parsed_args.class_name:
                filter_args['class_name'] = parsed_args.class_name
            if parsed_args.tag:
                filter_args['tag'] = parsed_args.tag

        data = client.packages.filter(**filter_args)

        columns = ('id', 'name', 'fully_qualified_name', 'author', 'active',
                   'is public', 'type', 'version')
        column_headers = [c.capitalize() for c in columns]
        if not parsed_args or parsed_args.limit == 0:
            return (
                column_headers,
                list(utils.get_item_properties(
                    s,
                    columns,
                ) for s in data)
            )
        else:
            return (
                column_headers,
                list(utils.get_item_properties(
                    s,
                    columns,
                ) for s in itertools.islice(data, parsed_args.limit))
            )
