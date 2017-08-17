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

import collections
import functools
import itertools
import os
import shutil
import six
import sys
import tempfile
import zipfile

from osc_lib.command import command
from osc_lib import exceptions as exc
from osc_lib import utils
from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_utils import strutils

from muranoclient.apiclient import exceptions
from muranoclient.common import exceptions as common_exceptions
from muranoclient.common import utils as murano_utils
from muranoclient.v1.package_creator import hot_package
from muranoclient.v1.package_creator import mpl_package


LOG = logging.getLogger(__name__)

DEFAULT_REPO_URL = "http://apps.openstack.org/api/v1/murano_repo/liberty/"

_bool_from_str_strict = functools.partial(
    strutils.bool_from_string, strict=True)


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


class DeletePackage(command.Lister):
    """Delete a package."""

    def get_parser(self, prog_name):
        parser = super(DeletePackage, self).get_parser(prog_name)
        parser.add_argument(
            'id',
            metavar="<ID>",
            nargs="+",
            help="Package ID to delete.",
        )

        return parser

    def take_action(self, parsed_args):
        LOG.debug("take_action({0})".format(parsed_args))

        client = self.app.client_manager.application_catalog

        failure_count = 0
        for package_id in parsed_args.id:
            try:
                client.packages.delete(package_id)
            except exceptions.NotFound:
                failure_count += 1
                print("Failed to delete '{0}'; package not found".
                      format(package_id))

        if failure_count == len(parsed_args.id):
            raise exceptions.CommandError("Unable to find and delete any of "
                                          "the specified packages.")
        data = client.packages.filter()

        columns = ('id', 'name', 'fully_qualified_name', 'author', 'active',
                   'is public', 'type', 'version')
        column_headers = [c.capitalize() for c in columns]

        return (
            column_headers,
            list(utils.get_item_properties(
                s,
                columns,
            ) for s in data)
        )


def _handle_package_exists(mc, data, package, exists_action):
    name = package.manifest['FullName']
    version = package.manifest.get('Version', '0')
    while True:
        print("Importing package {0}".format(name))
        try:
            return mc.packages.create(data, {name: package.file()})
        except common_exceptions.HTTPConflict:
            print("Importing package {0} failed. Package with the same"
                  " name/classes is already registered.".format(name))
            allowed_results = ['s', 'u', 'a']
            res = exists_action
            if not res:
                while True:
                    print("What do you want to do? (s)kip, (u)pdate, (a)bort")
                    res = six.moves.input()
                    if res in allowed_results:
                        break
            if res == 's':
                print("Skipping.")
                return None
            elif res == 'a':
                print("Exiting.")
                sys.exit()
            elif res == 'u':
                pkgs = list(mc.packages.filter(fqn=name, version=version,
                                               owned=True))
                if not pkgs:
                    msg = (
                        "Got a conflict response, but could not find the "
                        "package '{0}' in the current tenant.\nThis probably "
                        "means the conflicting package is in another tenant.\n"
                        "Please delete it manually."
                    ).format(name)
                    raise exceptions.CommandError(msg)
                elif len(pkgs) > 1:
                    msg = (
                        "Got {0} packages with name '{1}'.\nI do not trust "
                        "myself, please delete the package manually."
                    ).format(len(pkgs), name)
                    raise exceptions.CommandError(msg)
                print("Deleting package {0}({1})".format(name, pkgs[0].id))
                mc.packages.delete(pkgs[0].id)
                continue


class ImportPackage(command.Lister):
    """Import a package."""

    def get_parser(self, prog_name):
        parser = super(ImportPackage, self).get_parser(prog_name)
        parser.add_argument(
            'filename',
            metavar='<FILE>',
            nargs='+',
            help='URL of the murano zip package, FQPN, path to zip package'
                 ' or path to directory with package.'
        )
        parser.add_argument(
            '--categories',
            metavar='<CATEGORY>',
            nargs='*',
            help='Category list to attach.',
        )
        parser.add_argument(
            '--is-public',
            action='store_true',
            default=False,
            help="Make the package available for users from other tenants.",
        )
        parser.add_argument(
            '--package-version',
            default='',
            help='Version of the package to use from repository '
                 '(ignored when importing with multiple packages).'
        )
        parser.add_argument(
            '--exists-action',
            default='',
            choices=['a', 's', 'u'],
            help='Default action when a package already exists: '
                 '(s)kip, (u)pdate, (a)bort.'
        )
        parser.add_argument(
            '--dep-exists-action',
            default='',
            choices=['a', 's', 'u'],
            help='Default action when a dependency package already exists: '
                 '(s)kip, (u)pdate, (a)bort.'
        )
        parser.add_argument('--murano-repo-url',
                            default=murano_utils.env(
                                'MURANO_REPO_URL',
                                default=DEFAULT_REPO_URL),
                            help=('Defaults to env[MURANO_REPO_URL] '
                                  'or {0}'.format(DEFAULT_REPO_URL)))

        return parser

    def take_action(self, parsed_args):
        LOG.debug("take_action({0})".format(parsed_args))

        client = self.app.client_manager.application_catalog

        data = {"is_public": parsed_args.is_public}
        version = parsed_args.package_version
        if version and len(parsed_args.filename) >= 2:
            print("Requested to import more than one package, "
                  "ignoring version.")
            version = ''

        if parsed_args.categories:
            data["categories"] = parsed_args.categories

        total_reqs = collections.OrderedDict()
        main_packages_names = []
        for filename in parsed_args.filename:
            if os.path.isfile(filename) or os.path.isdir(filename):
                _file = filename
            else:
                print("Package file '{0}' does not exist, attempting to "
                      "download".format(filename))
                _file = murano_utils.to_url(
                    filename,
                    version=version,
                    base_url=parsed_args.murano_repo_url,
                    extension='.zip',
                    path='apps/',
                )
            try:
                package = murano_utils.Package.from_file(_file)
            except Exception as e:
                print("Failed to create package for '{0}', reason: {1}".format(
                    filename, e))
                continue
            total_reqs.update(
                package.requirements(base_url=parsed_args.murano_repo_url))
            main_packages_names.append(package.manifest['FullName'])

        imported_list = []

        dep_exists_action = parsed_args.dep_exists_action
        if dep_exists_action == '':
            dep_exists_action = parsed_args.exists_action

        for name, package in six.iteritems(total_reqs):
            image_specs = package.images()
            if image_specs:
                print("Inspecting required images")
                try:
                    imgs = murano_utils.ensure_images(
                        glance_client=client.glance_client,
                        image_specs=image_specs,
                        base_url=parsed_args.murano_repo_url,
                        is_package_public=parsed_args.is_public)
                    for img in imgs:
                        print("Added {0}, {1} image".format(
                            img['name'], img['id']))
                except Exception as e:
                    print("Error {0} occurred while installing "
                          "images for {1}".format(e, name))

            if name in main_packages_names:
                exists_action = parsed_args.exists_action
            else:
                exists_action = dep_exists_action
            try:
                imported_package = _handle_package_exists(
                    client, data, package, exists_action)
                if imported_package:
                    imported_list.append(imported_package)
            except Exception as e:
                print("Error {0} occurred while installing package {1}".format(
                    e, name))

        columns = ('id', 'name', 'fully_qualified_name', 'author', 'active',
                   'is public', 'type', 'version')
        column_headers = [c.capitalize() for c in columns]

        return (
            column_headers,
            list(utils.get_item_properties(
                s,
                columns,
            ) for s in imported_list)
        )


class ImportBundle(command.Lister):
    """Import a bundle."""

    def get_parser(self, prog_name):
        parser = super(ImportBundle, self).get_parser(prog_name)
        parser.add_argument(
            'filename',
            metavar='<FILE>',
            nargs='+',
            help='Bundle URL, bundle name, or path to the bundle file.'
        )
        parser.add_argument(
            '--is-public',
            action='store_true',
            default=False,
            help="Make the package available for users from other tenants.",
        )
        parser.add_argument(
            '--exists-action',
            default='',
            choices=['a', 's', 'u'],
            help='Default action when a package already exists: '
                 '(s)kip, (u)pdate, (a)bort.'
        )
        parser.add_argument('--murano-repo-url',
                            default=murano_utils.env(
                                'MURANO_REPO_URL',
                                default=DEFAULT_REPO_URL),
                            help=('Defaults to env[MURANO_REPO_URL] '
                                  'or {0}'.format(DEFAULT_REPO_URL)))

        return parser

    def take_action(self, parsed_args):

        LOG.debug("take_action({0})".format(parsed_args))

        client = self.app.client_manager.application_catalog

        total_reqs = collections.OrderedDict()
        for filename in parsed_args.filename:
            local_path = None
            if os.path.isfile(filename):
                _file = filename
                local_path = os.path.dirname(os.path.abspath(filename))
            else:
                print("Bundle file '{0}' does not exist, attempting "
                      "to download".format(filename))
                _file = murano_utils.to_url(
                    filename,
                    base_url=parsed_args.murano_repo_url,
                    path='bundles/',
                    extension='.bundle',
                )

            try:
                bundle_file = murano_utils.Bundle.from_file(_file)
            except Exception as e:
                print("Failed to create bundle for '{0}', reason: {1}".format(
                    filename, e))
                continue

            data = {"is_public": parsed_args.is_public}

            for package in bundle_file.packages(
                    base_url=parsed_args.murano_repo_url, path=local_path):

                requirements = package.requirements(
                    base_url=parsed_args.murano_repo_url,
                    path=local_path,
                )
                total_reqs.update(requirements)

        imported_list = []

        for name, dep_package in total_reqs.items():
            image_specs = dep_package.images()
            if image_specs:
                print("Inspecting required images")
                try:
                    imgs = parsed_args.ensure_images(
                        glance_client=client.glance_client,
                        image_specs=image_specs,
                        base_url=parsed_args.murano_repo_url,
                        local_path=local_path,
                        is_package_public=parsed_args.is_public)
                    for img in imgs:
                        print("Added {0}, {1} image".format(
                            img['name'], img['id']))
                except Exception as e:
                    print("Error {0} occurred while installing "
                          "images for {1}".format(e, name))
            try:
                imported_package = _handle_package_exists(
                    client, data, dep_package, parsed_args.exists_action)
                if imported_package:
                    imported_list.append(imported_package)
            except exceptions.CommandError:
                raise
            except Exception as e:
                print("Error {0} occurred while "
                      "installing package {1}".format(e, name))

        columns = ('id', 'name', 'fully_qualified_name', 'author', 'active',
                   'is public', 'type', 'version')
        column_headers = [c.capitalize() for c in columns]

        return (
            column_headers,
            list(utils.get_item_properties(
                s,
                columns,
            ) for s in imported_list)
        )


class ShowPackage(command.ShowOne):
    """Display details for a package."""

    def get_parser(self, prog_name):
        parser = super(ShowPackage, self).get_parser(prog_name)
        parser.add_argument(
            "id",
            metavar="<ID>",
            help=("Package ID to show."),
        )

        return parser

    def take_action(self, parsed_args):
        LOG.debug("take_action({0})".format(parsed_args))
        client = self.app.client_manager.application_catalog

        try:
            package = client.packages.get(parsed_args.id)
        except common_exceptions.HTTPNotFound:
            raise exceptions.CommandError("Package with id %s not "
                                          "found" % parsed_args.id)
        else:
            to_display = dict(
                id=package.id,
                type=package.type,
                owner_id=package.owner_id,
                name=package.name,
                fully_qualified_name=package.fully_qualified_name,
                is_public=package.is_public,
                enabled=package.enabled,
                class_definitions=jsonutils.dumps(package.class_definitions,
                                                  indent=2),
                categories=jsonutils.dumps(package.categories, indent=2),
                tags=jsonutils.dumps(package.tags, indent=2),
                description=package.description
            )

        return self.dict2columns(to_display)


class UpdatePackage(command.ShowOne):
    """Update an existing package."""

    def get_parser(self, prog_name):
        parser = super(UpdatePackage, self).get_parser(prog_name)
        parser.add_argument(
            'id',
            metavar="<ID>",
            help="Package ID to update.",
        )
        parser.add_argument(
            '--is-public',
            type=_bool_from_str_strict,
            metavar="{true|false}",
            help="Make package available to users from other tenants.",
        )
        parser.add_argument(
            '--enabled',
            type=_bool_from_str_strict,
            metavar="{true|false}",
            help="Make package active and available for deployments.",
        )
        parser.add_argument(
            '--name',
            default=None,
            help="New name for the package.",
        )
        parser.add_argument(
            '--description',
            default=None,
            help="New package description.",
        )
        parser.add_argument(
            '--tags',
            metavar='<TAG>', nargs='*',
            default=None,
            help="A list of keywords connected to the application.",
        )

        return parser

    def take_action(self, parsed_args):
        LOG.debug("take_action({0})".format(parsed_args))
        client = self.app.client_manager.application_catalog
        data = {}
        parameters = ('is_public', 'enabled',
                      'name', 'description',
                      'tags')
        for parameter in parameters:
            param_value = getattr(parsed_args, parameter, None)
            if param_value is not None:
                data[parameter] = param_value

        _, package = client.packages.update(parsed_args.id, data)

        to_display = dict(
            id=package["id"],
            type=package["type"],
            owner_id=package["owner_id"],
            name=package["name"],
            fully_qualified_name=package["fully_qualified_name"],
            is_public=package["is_public"],
            enabled=package["enabled"],
            class_definitions=jsonutils.dumps(package["class_definitions"],
                                              indent=2),
            categories=jsonutils.dumps(package["categories"], indent=2),
            tags=jsonutils.dumps(package["tags"], indent=2),
            description=package["description"]
        )

        return self.dict2columns(to_display)


class DownloadPackage(command.Command):
    """Download a package to a filename or stdout."""

    def get_parser(self, prog_name):
        parser = super(DownloadPackage, self).get_parser(prog_name)
        parser.add_argument(
            "id",
            metavar="<ID>",
            help=("Package ID to download."),
        )
        parser.add_argument(
            "filename",
            metavar="file", nargs="?",
            help=("Filename to save package to. If it is not "
                  "specified and there is no stdout redirection "
                  "the package won't be saved."),
        )

        return parser

    def take_action(self, parsed_args):
        LOG.debug("take_action({0})".format(parsed_args))
        client = self.app.client_manager.application_catalog

        def download_to_fh(package_id, fh):
            try:
                fh.write(client.packages.download(package_id))
            except common_exceptions.HTTPNotFound:
                raise exceptions.CommandError("Package with id %s not "
                                              "found" % parsed_args.id)

        if parsed_args.filename:
            with open(parsed_args.filename, 'wb') as fh:
                download_to_fh(parsed_args.id, fh)
                print("Package downloaded to %s" % parsed_args.filename)
        elif not sys.stdout.isatty():
            download_to_fh(parsed_args.id, sys.stdout)
        else:
            msg = ("No stdout redirection or local file specified for "
                   "downloaded package. Please specify a local file to "
                   "save downloaded package or redirect output to "
                   "another source.")
            raise exceptions.CommandError(msg)
