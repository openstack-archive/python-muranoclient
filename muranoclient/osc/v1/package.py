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

import os
import shutil
import tempfile
import zipfile

from muranoclient.v1.package_creator import hot_package
from muranoclient.v1.package_creator import mpl_package
from osc_lib.command import command
from osc_lib import exceptions as exc
from oslo_log import log as logging

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
