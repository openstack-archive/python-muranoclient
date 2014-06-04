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

import sys

from muranoclient.common import exceptions
from muranoclient.common import utils


def do_environment_list(mc, args={}):
    """List the environments."""
    environments = mc.environments.list()
    field_labels = ['ID', 'Name', 'Created', 'Updated']
    fields = ['id', 'name', 'created', 'updated']
    utils.print_list(environments, fields, field_labels, sortby=0)


@utils.arg("name", help="Environment name")
def do_environment_create(mc, args):
    """Create an environment."""
    mc.environments.create({"name": args.name})
    do_environment_list(mc)


@utils.arg("id", help="Environment id")
def do_environment_delete(mc, args):
    """Delete an environment."""
    try:
        mc.environments.delete(args.id)
    except exceptions.HTTPNotFound:
        raise exceptions.CommandError("Environment %s not found" % args.id)
    else:
        do_environment_list(mc)


@utils.arg("id", help="Environment id")
@utils.arg("name", help="Name to which the environment will be renamed")
def do_environment_rename(mc, args):
    """Rename an environment."""
    try:
        mc.environments.update(args.id, args.name)
    except exceptions.HTTPNotFound:
        raise exceptions.CommandError("Environment %s not found" % args.id)
    else:
        do_environment_list(mc)


@utils.arg("id", help="Environment id")
def do_environment_show(mc, args):
    """Display environment details."""
    try:
        environment = mc.environments.get(args.id)
    except exceptions.HTTPNotFound:
        raise exceptions.CommandError("Environment %s not found" % args.id)
    else:
        formatters = {
            "id": utils.text_wrap_formatter,
            "created": utils.text_wrap_formatter,
            "name": utils.text_wrap_formatter,
            "tenant_id": utils.text_wrap_formatter,
            "services": utils.json_formatter,

        }
        utils.print_dict(environment.to_dict(), formatters=formatters)


@utils.arg("environment_id",
           help="Environment id for which to list deployments")
def do_deployment_list(mc, args):
    """List deployments for an environment."""
    try:
        deployments = mc.deployments.list(args.environment_id)
    except exceptions.HTTPNotFound:
        raise exceptions.CommandError("Environment %s not found" % args.id)
    else:
        field_labels = ["ID", "State", "Created", "Updated", "Finished"]
        fields = ["id", "state", "created", "updated", "finished"]
        utils.print_list(deployments, fields, field_labels, sortby=0)


def do_category_list(mc, args):
    """List all available categories."""
    categories = mc.packages.categories()
    print(categories)


@utils.arg("--include-disabled", default=False, action="store_true")
def do_package_list(mc, args={}):
    """List available packages."""
    filter_args = {
        "include_disabled": getattr(args, 'include_disabled', False),
    }
    packages = mc.packages.filter(**filter_args)
    field_labels = ["ID", "Name", "FQN", "Author", "Is Public"]
    fields = ["id", "name", "fully_qualified_name", "author", "is_public"]
    utils.print_list(packages, fields, field_labels, sortby=0)


@utils.arg("package_id",
           help="Package ID to download")
@utils.arg("filename", metavar="file", nargs="?",
           help="Filename for download (defaults to stdout)")
def do_package_download(mc, args):
    """Download a package to a filename or stdout."""
    def download_to_fh(package_id, fh):
        fh.write(mc.packages.download(package_id))

    try:
        if not args.filename:
            download_to_fh(args.package_id, sys.stdout)
        else:
            with open(args.filename, 'wb') as fh:
                download_to_fh(args.package_id, fh)
                print("Package downloaded to %s" % args.filename)
    except exceptions.HTTPNotFound:
        raise exceptions.CommandError("Package %s not found" % args.package_id)


@utils.arg("package_id",
           help="Package ID to show")
def do_package_show(mc, args):
    """Display details for a package."""
    try:
        package = mc.packages.get(args.package_id)
    except exceptions.HTTPNotFound:
        raise exceptions.CommandError("Package %s not found" % args.package_id)
    else:
        to_display = dict(
            id=package.id,
            type=package.type,
            owner_id=package.owner_id,
            name=package.name,
            fully_qualified_name=package.fully_qualified_name,
            is_public=package.is_public,
            enabled=package.enabled,
            class_definitions=", ".join(package.class_definitions),
            categories=", ".join(package.categories),
            tags=", ".join(package.tags),
            description=package.description
        )
        formatters = {
            'class_definitions': utils.text_wrap_formatter,
            'categories': utils.text_wrap_formatter,
            'tags': utils.text_wrap_formatter,
            'description': utils.text_wrap_formatter,
        }
        utils.print_dict(to_display, formatters)


@utils.arg("package_id",
           help="Package ID to delete")
def do_package_delete(mc, args):
    """Delete a package."""
    try:
        mc.packages.delete(args.package_id)
    except exceptions.HTTPNotFound:
        raise exceptions.CommandError("Package %s not found" % args.package_id)
    else:
        do_package_list(mc)


@utils.arg("filename", metavar="file", help="Zip file containing package")
@utils.arg("category", nargs="+",
           help="One or more categories to which the package belongs")
def do_package_import(mc, args):
    """Import a package. `file` should be the path to a zip file."""
    data = {"categories": args.category}
    mc.packages.create(data, ((args.filename, open(args.filename, 'rb')),))
    do_package_list(mc)
