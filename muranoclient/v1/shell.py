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

import collections
import functools
import json
import os
import shutil
import sys
import tempfile
import uuid
import zipfile

import jsonpatch
from oslo_utils import strutils
import six
import six.moves

from muranoclient.common import exceptions as common_exceptions
from muranoclient.common import utils
from muranoclient.openstack.common.apiclient import exceptions
from muranoclient.v1.package_creator import hot_package
from muranoclient.v1.package_creator import mpl_package

_bool_from_str_strict = functools.partial(
    strutils.bool_from_string, strict=True)

DEFAULT_PAGE_SIZE = 20


@utils.arg('--all-tenants', action='store_true', default=False,
           help='Allows to list environments from all tenants'
                ' (admin only).')
def do_environment_list(mc, args=None):
    """List the environments."""
    if args is None:
        args = {}
    all_tenants = getattr(args, 'all_tenants', False)
    environments = mc.environments.list(all_tenants)
    _print_environment_list(environments)


def _print_environment_list(environments):
    field_labels = ['ID', 'Name', 'Status', 'Created', 'Updated']
    fields = ['id', 'name', 'status', 'created', 'updated']
    utils.print_list(environments, fields, field_labels, sortby=0)


def _generate_join_existing_net(net, subnet):
    res = {
        'defaultNetworks': {
            'environment': {
                '?': {
                    'id': uuid.uuid4().hex,
                    'type': 'io.murano.resources.ExistingNeutronNetwork'
                },
            },
            'flat': None
        }
    }
    if net:
        res['defaultNetworks']['environment']['internalNetworkName'] = net
    if subnet:
        res['defaultNetworks']['environment']['internalSubnetworkName'] = \
            subnet
    return res


@utils.arg("--join-net-id", metavar="<NET_ID>",
           help="Network id to join.",)
@utils.arg("--join-subnet-id", metavar="<SUBNET_ID>",
           help="Subnetwork id to join.",)
@utils.arg("--region", metavar="<REGION_NAME>",
           help="Name of the target OpenStack region.",)
@utils.arg("name", metavar="<ENVIRONMENT_NAME>",
           help="Environment name.")
def do_environment_create(mc, args):
    """Create an environment."""
    body = {"name": args.name, "region": args.region}
    if args.join_net_id or args.join_subnet_id:
        body.update(_generate_join_existing_net(
            args.join_net_id, args.join_subnet_id))
    environment = mc.environments.create(body)
    _print_environment_list([environment])


@utils.arg("id", metavar="<NAME or ID>",
           nargs="+", help="Id or name of environment(s) to delete.")
@utils.arg('--abandon', action='store_true', default=False,
           help='If set will abandon environment without deleting any'
                ' of its resources.')
def do_environment_delete(mc, args):
    """Delete an environment."""
    abandon = getattr(args, 'abandon', False)
    failure_count = 0
    for environment_id in args.id:
        try:
            environment = utils.find_resource(mc.environments, environment_id)
            mc.environments.delete(environment.id, abandon)
        except exceptions.NotFound:
            failure_count += 1
            print("Failed to delete '{0}'; environment not found".
                  format(environment_id))
    if failure_count == len(args.id):
        raise exceptions.CommandError("Unable to find and delete any of the "
                                      "specified environments.")
    do_environment_list(mc)


@utils.arg("id", metavar="<NAME or ID>",
           help="Environment ID or name.")
@utils.arg("name", metavar="<ENVIRONMENT_NAME>",
           help="A name to which the environment will be renamed.")
def do_environment_rename(mc, args):
    """Rename an environment."""
    try:
        environment = utils.find_resource(mc.environments, args.id)
        environment = mc.environments.update(environment.id, args.name)
    except exceptions.NotFound:
        raise exceptions.CommandError("Environment %s not found" % args.id)
    else:
        _print_environment_list([environment])


@utils.arg("id", metavar="<NAME or ID>",
           help="Environment ID or name.")
@utils.arg("--session-id", metavar="<SESSION_ID>", default='',
           help="Id of a config session.")
@utils.arg("--only-apps", action='store_true',
           help="Only print apps of the environment (useful for automation).")
def do_environment_show(mc, args):
    """Display environment details."""
    try:
        environment = utils.find_resource(
            mc.environments, args.id, session_id=args.session_id)
    except exceptions.NotFound:
        raise exceptions.CommandError("Environment %s not found" % args.id)
    else:
        if getattr(args, 'only_apps', False):
            print(utils.json_formatter(environment.services))
        else:
            formatters = {
                "id": utils.text_wrap_formatter,
                "created": utils.text_wrap_formatter,
                "name": utils.text_wrap_formatter,
                "tenant_id": utils.text_wrap_formatter,
                "services": utils.json_formatter,

            }
            utils.print_dict(environment.to_dict(), formatters=formatters)


@utils.arg("id", metavar="<ID>",
           help="ID of Environment to deploy.")
@utils.arg("--session-id", metavar="<SESSION>",
           required=True,
           help="ID of configuration session to deploy.")
def do_environment_deploy(mc, args):
    """Start deployment of a murano environment session."""
    mc.sessions.deploy(args.id, args.session_id)
    do_environment_show(mc, args)


@utils.arg("id", help="ID of Environment to call action against.")
@utils.arg("--action-id", metavar="<ACTION>",
           required=True,
           help="ID of action to run.")
@utils.arg("--arguments", metavar='<KEY=VALUE>', nargs='*',
           help="Action arguments.")
def do_environment_action_call(mc, args):
    """Call action `ACTION` in environment `ID`.

    Returns id of an asynchronous task, that executes the action.
    Actions can only be called on a `deployed` environment.
    To view actions available in a given environment use `environment-show`
    command.
    """
    arguments = {}
    for argument in args.arguments or []:
        if '=' not in argument:
            raise exceptions.CommandError(
                "Argument should be in form of KEY=VALUE. Found: {0}".format(
                    argument))
        k, v = argument.split('=', 1)
        try:
            v = json.loads(v)
        except ValueError:
            # treat value as a string if it doesn't load as json
            pass
        arguments[k] = v
    task_id = mc.actions.call(
        args.id, args.action_id, arguments=arguments)
    print("Created task, id: {0}".format(task_id))


@utils.arg("id", metavar="<ID>",
           help="ID of Environment where task is being executed.")
@utils.arg("--task-id", metavar="<TASK>",
           required=True,
           help="ID of action to run.")
def do_environment_action_get_result(mc, args):
    """Get result of `TASK` in environment `ID`."""
    result = mc.actions.get_result(args.id, args.task_id)
    print("Task id result: {0}".format(result))


@utils.arg("class_name", metavar='<CLASS>',
           help="FQN of the class with static method")
@utils.arg("method_name", metavar='<METHOD>', help="Static method to run")
@utils.arg("--arguments", metavar='<KEY=VALUE>', nargs='*',
           help="Method arguments. No arguments by default")
@utils.arg("--package-name", metavar='<PACKAGE>', default='',
           help='Optional FQN of the package to look for the class in')
@utils.arg("--class-version", default='',
           help='Optional version of the class, otherwise version =0 is '
                'used ')
def do_static_action_call(mc, args):
    """Call static method `METHOD` of the class `CLASS` with `ARGUMENTS`.

    Returns the result of the method execution.
    `PACKAGE` and `CLASS_VERSION` can be specified optionally to find class in
    a particular package and to look for the specific version of a class
    respectively.
    """
    arguments = {}
    for argument in args.arguments or []:
        if '=' not in argument:
            raise exceptions.CommandError(
                "Argument should be in form of KEY=VALUE. Found: {0}".format(
                    argument))
        key, value = argument.split('=', 1)
        try:
            value = json.loads(value)
        except ValueError:
            # treat value as a string if it doesn't load as json
            pass
        arguments[key] = value

    request_body = {
        "className": args.class_name,
        "methodName": args.method_name,
        "packageName": args.package_name or None,
        "classVersion": args.class_version or '=0',
        "parameters": arguments
    }

    print("Waiting for result...")
    try:
        result = mc.static_actions.call(request_body).get_result()
        print("Static action result: {0}".format(result))
    except Exception as e:
        print(str(e))


@utils.arg("id", metavar="<ID>", help="ID of Environment to add session to.")
def do_environment_session_create(mc, args):
    """Creates a new configuration session for environment ID."""
    environment_id = args.id
    session_id = mc.sessions.configure(environment_id).id
    print("Created new session:")
    formatters = {"id": utils.text_wrap_formatter}
    utils.print_dict({"id": session_id}, formatters=formatters)


@utils.arg("id", metavar="<ID>", help="ID of Environment to edit.")
@utils.arg("filename", metavar="FILE", nargs="?",
           help="File to read jsonpatch from (defaults to stdin).")
@utils.arg("--session-id", metavar="<SESSION_ID>",
           required=True,
           help="Id of a config session.")
def do_environment_apps_edit(mc, args):
    """Edit environment's object model.

    `FILE` is path to a file, that contains jsonpatch, that describes changes
    to be made to environment's object-model.

    [
        { "op": "add", "path": "/-",
           "value": { ... your-app object model here ... }
        },
        { "op": "replace", "path": "/0/?/name",
          "value": "new_name"
        },
    ]

    NOTE: Values '===id1===', '===id2===', etc. in the resulting object-model
    will be substituted with uuids.

    For more info on jsonpatch see RFC 6902
    """

    jp_obj = None
    if not args.filename:
        jp_obj = json.load(sys.stdin)
    else:
        with open(args.filename) as fpatch:
            jp_obj = json.load(fpatch)

    jpatch = jsonpatch.JsonPatch(jp_obj)

    environment_id = args.id
    session_id = args.session_id
    environment = mc.environments.get(environment_id, session_id)

    object_model = jpatch.apply(environment.services)
    utils.traverse_and_replace(object_model)

    mc.services.put(
        environment_id,
        path='/',
        data=jpatch.apply(environment.services),
        session_id=session_id)


def do_env_template_list(mc, args=None):
    """List the environments templates."""
    if args is None:
        args = {}
    env_templates = mc.env_templates.list()
    _print_env_template_list(env_templates)


def _print_env_template_list(env_templates):
    field_labels = ['ID', 'Name', 'Created', 'Updated', 'Is public']
    fields = ['id', 'name', 'created', 'updated', 'is_public']
    utils.print_list(env_templates, fields, field_labels, sortby=0)


@utils.arg("name", metavar="<ENV_TEMPLATE_NAME>",
           help="Environment template name.")
@utils.arg("--is-public", action='store_true', default=False,
           help='Make the template available for users from other tenants.')
def do_env_template_create(mc, args):
    """Create an environment template."""
    env_template = mc.env_templates.create(
        {"name": args.name, "is_public": args.is_public})
    _print_env_template_list([env_template])


@utils.arg("id", metavar="<ID>",
           help="Environment template ID.")
@utils.arg("name", metavar="<ENV_NAME>",
           help="New environment name.")
def do_env_template_create_env(mc, args):
    """Create a new environment from template."""
    try:
        template = mc.env_templates.create_env(args.id, args.name)
    except common_exceptions.HTTPNotFound:
        raise exceptions.CommandError("Environment template %s not found"
                                      % args.id)
    else:
        formatters = {
            "environment_id": utils.text_wrap_formatter,
            "session_id": utils.text_wrap_formatter
        }
        utils.print_dict(template.to_dict(), formatters=formatters)


@utils.arg("id", metavar="<ID>",
           help="Environment template ID.")
def do_env_template_show(mc, args):
    """Display environment template details."""
    try:
        env_template = mc.env_templates.get(args.id)
    except common_exceptions.HTTPNotFound:
        raise exceptions.CommandError("Environment template %s not found"
                                      % args.id)
    else:
        formatters = {
            "id": utils.text_wrap_formatter,
            "created": utils.text_wrap_formatter,
            "name": utils.text_wrap_formatter,
            "tenant_id": utils.text_wrap_formatter,
            "services": utils.json_formatter,

        }
        utils.print_dict(env_template.to_dict(), formatters=formatters)


@utils.arg("id", metavar="<ENV_TEMPLATE_ID>",
           help="Environment template ID.")
@utils.arg('app_template_file', metavar='<FILE>',
           help='Path to the template.')
def do_env_template_add_app(mc, args):
    """Add application to the environment template."""
    with open(args.app_template_file, "r") as app_file:
        app_templates = json.load(app_file)
    if not isinstance(app_templates, list):
        app_templates = [app_templates]
    for app_template in app_templates:
        mc.env_templates.create_app(args.id, app_template)
    do_env_template_show(mc, args)


@utils.arg("id", metavar="<ENV_TEMPLATE_ID>",
           help="Environment template ID.")
@utils.arg("app_id", metavar="<ENV_TEMPLATE_APP_ID>",
           help="Application ID.")
def do_env_template_del_app(mc, args):
    """Delete application from the environment template."""
    mc.env_templates.delete_app(args.id, args.app_id)
    do_env_template_show(mc, args)


@utils.arg("id", metavar="<ID>",
           help="Environment template ID.")
@utils.arg("name", metavar="<ENV_TEMPLATE_NAME>",
           help="Environment template name.")
def do_env_template_update(mc, args):
    """Update an environment template."""
    env_template = mc.env_templates.update(args.id, args.name)
    _print_env_template_list([env_template])


@utils.arg("id", metavar="<ID>",
           nargs="+", help="ID of environment(s) template to delete.")
def do_env_template_delete(mc, args):
    """Delete an environment template."""
    failure_count = 0
    for env_template_id in args.id:
        try:
            mc.env_templates.delete(env_template_id)
        except common_exceptions.HTTPNotFound:
            failure_count += 1
            mns = "Failed to delete '{0}'; environment template not found".\
                format(env_template_id)

    if failure_count == len(args.id):
        raise exceptions.CommandError(mns)
    do_env_template_list(mc)


@utils.arg("id", metavar="<ID>",
           help="Environment template ID.")
@utils.arg("name", metavar="<ENV_TEMPLATE_NAME>",
           help="New environment template name.")
def do_env_template_clone(mc, args):
    """Create a new template, cloned from template."""
    try:
        env_template = mc.env_templates.clone(args.id, args.name)
    except common_exceptions.HTTPNotFound:
        raise exceptions.CommandError("Environment template %s not found"
                                      % args.id)
    else:
        formatters = {
            "id": utils.text_wrap_formatter,
            "created": utils.text_wrap_formatter,
            "updated": utils.text_wrap_formatter,
            "version": utils.text_wrap_formatter,
            "name": utils.text_wrap_formatter,
            "tenant_id": utils.text_wrap_formatter,
            "is_public": utils.text_wrap_formatter,
            "services": utils.json_formatter,

        }
        utils.print_dict(env_template.to_dict(), formatters=formatters)


@utils.arg("id", metavar="<ID>",
           help="Environment ID for which to list deployments.")
def do_deployment_list(mc, args):
    """List deployments for an environment."""
    try:
        environment = utils.find_resource(mc.environments, args.id)
        deployments = mc.deployments.list(environment.id)
    except exceptions.NotFound:
        raise exceptions.CommandError("Environment %s not found" % args.id)
    else:
        field_labels = ["ID", "State", "Created", "Updated", "Finished"]
        fields = ["id", "state", "created", "updated", "finished"]
        utils.print_list(deployments, fields, field_labels, sortby=0)


@utils.arg("--limit", type=int, default=DEFAULT_PAGE_SIZE)
@utils.arg("--include-disabled", default=False, action="store_true")
@utils.arg("--owned", default=False, action="store_true")
@utils.arg('--search', metavar='<SEARCH_KEYS>',
           dest='search', required=False,
           help='Show packages, that match search keys fuzzily')
@utils.arg('--name', metavar='<PACKAGE_NAME>',
           dest='name', required=False,
           help='Show packages, whose name match parameter exactly')
@utils.arg('--fqn', metavar="<PACKAGE_FULLY_QUALIFIED_NAME>",
           dest='fqn', required=False,
           help='Show packages, '
                'whose fully qualified name match parameter exactly')
@utils.arg('--type', metavar='<PACKAGE_TYPE>',
           dest='type', required=False,
           help='Show packages, whose type match parameter exactly')
@utils.arg('--category', metavar='<PACKAGE_CATEGORY>',
           dest='category', required=False,
           help='Show packages, whose categories include parameter')
@utils.arg('--class_name', metavar='<PACKAGE_CLASS_NAME>',
           dest='class_name', required=False,
           help='Show packages, whose class name match parameter exactly')
@utils.arg('--tag', metavar='<PACKAGE_TAG>',
           dest='tag', required=False,
           help='Show packages, whose tags include parameter')
def do_package_list(mc, args=None):
    """List available packages."""
    if args is None:
        args = {}
    filter_args = {
        "include_disabled": getattr(args, 'include_disabled', False),
        "limit": getattr(args, 'limit', DEFAULT_PAGE_SIZE),
        "owned": getattr(args, 'owned', False),
    }
    if args:
        if args.search:
            filter_args['search'] = args.search
        if args.name:
            filter_args['name'] = args.name
        if args.fqn:
            filter_args['fqn'] = args.fqn
        if args.type:
            filter_args['type'] = args.type
        if args.category:
            filter_args['category'] = args.category
        if args.class_name:
            filter_args['class_name'] = args.class_name
        if args.tag:
            filter_args['tag'] = args.tag

    packages = mc.packages.filter(**filter_args)
    _print_package_list(packages)


def _print_package_list(packages):
    field_labels = ["ID", "Name", "FQN", "Author", "Active",
                    "Is Public", "Type", "Version"]
    fields = ["id", "name", "fully_qualified_name", "author",
              "enabled", "is_public", "type", "version"]
    utils.print_list(packages, fields, field_labels, sortby=0)


@utils.arg("id", metavar="<ID>",
           help="Package ID to download.")
@utils.arg("filename", metavar="file", nargs="?",
           help="Filename to save package to. If it is not specified and "
                "there is no stdout redirection the package won't be saved.")
def do_package_download(mc, args):
    """Download a package to a filename or stdout."""

    def download_to_fh(package_id, fh):
        fh.write(mc.packages.download(package_id))

    try:
        if args.filename:
            with open(args.filename, 'wb') as fh:
                download_to_fh(args.id, fh)
                print("Package downloaded to %s" % args.filename)
        elif not sys.stdout.isatty():
            download_to_fh(args.id, sys.stdout)
        else:
            msg = ('No stdout redirection or local file specified for '
                   'downloaded package. Please specify a local file to save '
                   'downloaded package or redirect output to another source.')
            raise exceptions.CommandError(msg)
    except common_exceptions.HTTPNotFound:
        raise exceptions.CommandError("Package %s not found" % args.id)


@utils.arg("id", metavar="<ID>",
           help="Package ID to show.")
def do_package_show(mc, args):
    """Display details for a package."""
    try:
        package = mc.packages.get(args.id)
    except common_exceptions.HTTPNotFound:
        raise exceptions.CommandError("Package %s not found" % args.id)
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


@utils.arg("id", metavar="<ID>",
           nargs='+', help="Package ID to delete.")
def do_package_delete(mc, args):
    """Delete a package."""
    failure_count = 0
    for package_id in args.id:
        try:
            mc.packages.delete(package_id)
            print("Deleted package '{0}'".format(package_id))
        except exceptions.NotFound:
            failure_count += 1
            print("Failed to delete '{0}'; package not found".
                  format(package_id))

    if failure_count == len(args.id):
        raise exceptions.CommandError("Unable to find and delete any of the "
                                      "specified packages.")
    else:
        do_package_list(mc)


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


@utils.arg('filename', metavar='<FILE>',
           nargs='+',
           help='URL of the murano zip package, FQPN, or path to zip package.')
@utils.arg('-c', '--categories', metavar='<CATEGORY>', nargs='*',
           help='Category list to attach.')
@utils.arg('--is-public', action='store_true', default=False,
           help='Make the package available for users from other tenants.')
@utils.arg('--package-version', default='',
           help='Version of the package to use from repository '
                '(ignored when importing with multiple packages).')
@utils.arg('--exists-action', default='', choices=['a', 's', 'u'],
           help='Default action when a package already exists: '
                '(s)kip, (u)pdate, (a)bort.')
@utils.arg('--dep-exists-action', default='', choices=['a', 's', 'u'],
           help='Default action when a dependency package already exists: '
                '(s)kip, (u)pdate, (a)bort.')
def do_package_import(mc, args):
    """Import a package.

    `FILE` can be either a path to a zip file, url or a FQPN.
    You can use `--` to separate `FILE`s from other arguments.

    Categories have to be separated with a space and have to be already
    present in murano.
    """
    data = {"is_public": args.is_public}

    version = args.package_version
    if version and len(args.filename) >= 2:
        print("Requested to import more than one package, "
              "ignoring version.")
        version = ''

    if args.categories:
        data["categories"] = args.categories

    total_reqs = collections.OrderedDict()
    main_packages_names = []
    for filename in args.filename:
        if os.path.isfile(filename):
            _file = filename
        else:
            print("Package file '{0}' does not exist, attempting to download"
                  "".format(filename))
            _file = utils.to_url(
                filename,
                version=version,
                base_url=args.murano_repo_url,
                extension='.zip',
                path='apps/',
            )
        try:
            package = utils.Package.from_file(_file)
        except Exception as e:
            print("Failed to create package for '{0}', reason: {1}".format(
                filename, e))
            continue
        total_reqs.update(package.requirements(base_url=args.murano_repo_url))
        main_packages_names.append(package.manifest['FullName'])

    imported_list = []

    dep_exists_action = args.dep_exists_action
    if dep_exists_action == '':
        dep_exists_action = args.exists_action

    for name, package in six.iteritems(total_reqs):
        image_specs = package.images()
        if image_specs:
            print("Inspecting required images")
            try:
                imgs = utils.ensure_images(
                    glance_client=mc.glance_client,
                    image_specs=image_specs,
                    base_url=args.murano_repo_url,
                    is_package_public=args.is_public)
                for img in imgs:
                    print("Added {0}, {1} image".format(
                        img['name'], img['id']))
            except Exception as e:
                print("Error {0} occurred while installing "
                      "images for {1}".format(e, name))
        if name in main_packages_names:
            exists_action = args.exists_action
        else:
            exists_action = dep_exists_action
        try:
            imported_package = _handle_package_exists(
                mc, data, package, exists_action)
            if imported_package:
                imported_list.append(imported_package)
        except Exception as e:
            print("Error {0} occurred while installing package {1}".format(
                e, name))

    if imported_list:
        _print_package_list(imported_list)


@utils.arg("id", metavar="<ID>",
           help="Package ID to update.")
@utils.arg('--is-public', type=_bool_from_str_strict, metavar='{true|false}',
           help='Make package available to users from other tenants.')
@utils.arg('--enabled', type=_bool_from_str_strict, metavar='{true|false}',
           help='Make package active and available for deployments.')
@utils.arg('--name', default=None, help='New name for the package.')
@utils.arg('--description', default=None, help='New package description.')
@utils.arg('--tags', metavar='<TAG>', nargs='*',
           default=None,
           help='A list of keywords connected to the application.')
def do_package_update(mc, args):
    """Update an existing package."""
    data = {}
    parameters = ('is_public', 'enabled',
                  'name', 'description',
                  'tags')
    for parameter in parameters:
        param_value = getattr(args, parameter, None)
        if param_value is not None:
            data[parameter] = param_value

    mc.packages.update(args.id, data)
    do_package_show(mc, args)


@utils.arg('filename', metavar='<FILE>',
           nargs='+',
           help='Bundle URL, bundle name, or path to the bundle file.')
@utils.arg('--is-public', action='store_true', default=False,
           help='Make packages available to users from other tenants.')
@utils.arg('--exists-action', default='', choices=['a', 's', 'u'],
           help='Default action when a package already exists.')
def do_bundle_import(mc, args):
    """Import a bundle.

    `FILE` can be either a path to a zip file, URL, or name from repo.
    If `FILE` is a local file, treat names of packages in a bundle as
    file names, relative to location of the bundle file. Requirements
    are first searched in the same directory.
    """
    total_reqs = collections.OrderedDict()
    for filename in args.filename:
        local_path = None
        if os.path.isfile(filename):
            _file = filename
            local_path = os.path.dirname(os.path.abspath(filename))
        else:
            print("Bundle file '{0}' does not exist, attempting to download"
                  "".format(filename))
            _file = utils.to_url(
                filename,
                base_url=args.murano_repo_url,
                path='bundles/',
                extension='.bundle',
            )

        try:
            bundle_file = utils.Bundle.from_file(_file)
        except Exception as e:
            print("Failed to create bundle for '{0}', reason: {1}".format(
                filename, e))
            continue

        data = {"is_public": args.is_public}

        for package in bundle_file.packages(
                base_url=args.murano_repo_url, path=local_path):

            requirements = package.requirements(
                base_url=args.murano_repo_url,
                path=local_path,
            )
            total_reqs.update(requirements)

    imported_list = []

    for name, dep_package in six.iteritems(total_reqs):
        image_specs = dep_package.images()
        if image_specs:
            print("Inspecting required images")
            try:
                imgs = utils.ensure_images(
                    glance_client=mc.glance_client,
                    image_specs=image_specs,
                    base_url=args.murano_repo_url,
                    local_path=local_path,
                    is_package_public=args.is_public)
                for img in imgs:
                    print("Added {0}, {1} image".format(
                        img['name'], img['id']))
            except Exception as e:
                print("Error {0} occurred while installing "
                      "images for {1}".format(e, name))
        try:
            imported_package = _handle_package_exists(
                mc, data, dep_package, args.exists_action)
            if imported_package:
                imported_list.append(imported_package)
        except exceptions.CommandError:
            raise
        except Exception as e:
            print("Error {0} occurred while "
                  "installing package {1}".format(e, name))
    if imported_list:
        _print_package_list(imported_list)


def _handle_save_packages(packages, dst, base_url, no_images):
    downloaded_images = []

    for name, pkg in six.iteritems(packages):
        if not no_images:
            image_specs = pkg.images()
            for image_spec in image_specs:
                if not image_spec["Name"]:
                    print("Invalid image.lst file for {0} package. "
                          "'Name' section is absent.".format(name))
                    continue
                if image_spec["Name"] not in downloaded_images:
                    print("Package {0} depends on image {1}. "
                          "Downloading...".format(name, image_spec["Name"]))
                    try:
                        utils.save_image_local(image_spec, base_url, dst)
                        downloaded_images.append(image_spec["Name"])
                    except Exception as e:
                        print("Error {0} occurred while saving image {1}".
                              format(e, image_spec["Name"]))

        try:
            pkg.save(dst)
            print("Package {0} has been successfully saved".format(name))
        except Exception as e:
            print("Error {0} occurred while saving package {1}".format(
                e, name))


@utils.arg('filename', metavar='<BUNDLE>',
           help='Bundle URL, bundle name, or path to the bundle file.')
@utils.arg('-p', '--path', metavar='<PATH>',
           help='Path to the directory to store packages. If not set will use '
                'current directory.')
@utils.arg('--no-images', action='store_true', default=False,
           help='If set will skip images downloading.')
def do_bundle_save(mc, args):
    """Save a bundle.

    This will download a bundle of packages with all dependencies
    to specified path. If path doesn't exist it will be created.
    """

    bundle = args.filename
    base_url = args.murano_repo_url

    if args.path:
        if not os.path.exists(args.path):
            os.makedirs(args.path)
        dst = args.path
    else:
        dst = os.getcwd()

    total_reqs = collections.OrderedDict()

    if os.path.isfile(bundle):
        _file = bundle
    else:
        print("Bundle file '{0}' does not exist, attempting to download"
              .format(bundle))
        _file = utils.to_url(
            bundle,
            base_url=base_url,
            path='bundles/',
            extension='.bundle',
        )
    try:
        bundle_file = utils.Bundle.from_file(_file)
    except Exception as e:
        msg = "Failed to create bundle for {0}, reason: {1}".format(bundle, e)
        raise exceptions.CommandError(msg)

    for package in bundle_file.packages(base_url=base_url):
        requirements = package.requirements(base_url=base_url)
        total_reqs.update(requirements)

    no_images = getattr(args, 'no_images', False)

    _handle_save_packages(total_reqs, dst, base_url, no_images)

    try:
        bundle_file.save(dst, binary=False)
        print("Bundle file {0} has been successfully saved".format(bundle))
    except Exception as e:
        print("Error {0} occurred while saving bundle {1}".format(e, bundle))


@utils.arg('package', metavar='<PACKAGE>',
           nargs='+',
           help='Package URL or name.')
@utils.arg('-p', '--path', metavar='<PATH>',
           help='Path to the directory to store package. If not set will use '
                'current directory.')
@utils.arg('--package-version', default='',
           help='Version of the package to use from repository '
                '(ignored when saving with multiple packages).')
@utils.arg('--no-images', action='store_true', default=False,
           help='If set will skip images downloading.')
def do_package_save(mc, args):
    """Save a package.

    This will download package(s) with all dependencies
    to specified path. If path doesn't exist it will be created.
    """
    base_url = args.murano_repo_url

    if args.path:
        if not os.path.exists(args.path):
            os.makedirs(args.path)
        dst = args.path
    else:
        dst = os.getcwd()

    version = args.package_version
    if version and len(args.filename) >= 2:
        print("Requested to save more than one package, "
              "ignoring version.")
        version = ''

    total_reqs = collections.OrderedDict()
    for package in args.package:
        _file = utils.to_url(
            package,
            version=version,
            base_url=base_url,
            extension='.zip',
            path='apps/',
        )
        try:
            pkg = utils.Package.from_file(_file)
        except Exception as e:
            print("Failed to create package for '{0}', reason: {1}".format(
                package, e))
            continue
        total_reqs.update(pkg.requirements(base_url=base_url))

    no_images = getattr(args, 'no_images', False)

    _handle_save_packages(total_reqs, dst, base_url, no_images)


@utils.arg('id', metavar='<ID>',
           help='Environment ID to show applications from.')
@utils.arg('-p', '--path', metavar='<PATH>',
           help='Level of detalization to show. '
                'Leave empty to browse all applications in the environment.',
           default='/')
def do_app_show(mc, args):
    """List applications, added to specified environment."""
    if args.path == '/':
        apps = mc.services.list(args.id)
        formatters = {'id': lambda x: getattr(x, '?')['id'],
                      'type': lambda x: getattr(x, '?')['type']}
        field_labels = ['Id', 'Name', 'Type']
        fields = ['id', 'name', 'type']
        utils.print_list(apps, fields, field_labels, formatters=formatters)
    else:
        if not args.path.startswith('/'):
            args.path = '/' + args.path
        app = mc.services.get(args.id, args.path)

        # If app with specified path is not found, it is empty.
        if hasattr(app, '?'):
            formatters = {}
            for key in app.to_dict().keys():
                formatters[key] = utils.json_formatter
            utils.print_dict(app.to_dict(), formatters)
        else:
            raise exceptions.CommandError("Could not find application at path"
                                          " %s" % args.path)


@utils.arg('-t', '--template', metavar='<HEAT_TEMPLATE>',
           help='Path to the Heat template to import as '
                'an Application Definition.')
@utils.arg('-c', '--classes-dir', metavar='<CLASSES_DIRECTORY>',
           help='Path to the directory containing application classes.')
@utils.arg('-r', '--resources-dir', metavar='<RESOURCES_DIRECTORY>',
           help='Path to the directory containing application resources.')
@utils.arg('-n', '--name', metavar='<DISPLAY_NAME>',
           help='Display name of the Application in Catalog.')
@utils.arg('-f', '--full-name', metavar='<full-name>',
           help='Fully-qualified name of the Application in Catalog.')
@utils.arg('-a', '--author', metavar='<AUTHOR>', help='Name of the publisher.')
@utils.arg('--tags', help='A list of keywords connected to the application.',
           metavar='<TAG1 TAG2>', nargs='*')
@utils.arg('-d', '--description', metavar='<DESCRIPTION>',
           help='Detailed description for the Application in Catalog.')
@utils.arg('-o', '--output', metavar='<PACKAGE_NAME>',
           help='The name of the output file archive to save locally.')
@utils.arg('-u', '--ui', metavar='<UI_DEFINITION>',
           help='Dynamic UI form definition.')
@utils.arg('--type',
           help='Package type. Possible values: Application or Library.')
@utils.arg('-l', '--logo', metavar='<LOGO>', help='Path to the package logo.')
def do_package_create(mc, args):
    """Create an application package."""
    if args.template and args.classes_dir:
        raise exceptions.CommandError(
            "Provide --template for a HOT-based package, OR"
            " --classes-dir for a MuranoPL-based package")
    if not args.template and not args.classes_dir:
        raise exceptions.CommandError(
            "Provide --template for a HOT-based package, OR at least"
            " --classes-dir for a MuranoPL-based package")
    directory_path = None
    try:
        archive_name = args.output if args.output else None
        if args.template:
            directory_path = hot_package.prepare_package(args)
            if not archive_name:
                archive_name = os.path.basename(args.template)
                archive_name = os.path.splitext(archive_name)[0] + ".zip"
        else:
            directory_path = mpl_package.prepare_package(args)
            if not archive_name:
                archive_name = tempfile.mkstemp(
                    prefix="murano_", dir=os.getcwd())[1] + ".zip"

        _make_archive(archive_name, directory_path)
        print("Application package is available at " +
              os.path.abspath(archive_name))
    finally:
        if directory_path:
            shutil.rmtree(directory_path)


def _make_archive(archive_name, path):
    zip_file = zipfile.ZipFile(archive_name, 'w')
    for root, dirs, files in os.walk(path):
        for f in files:
            zip_file.write(os.path.join(root, f),
                           arcname=os.path.join(os.path.relpath(root, path),
                                                f))


def do_category_list(mc, args=None):
    """List all available categories."""
    if args is None:
        args = {}
    categories = mc.categories.list()
    _print_category_list(categories)


def _print_category_list(categories):
    field_labels = ["ID", "Name"]
    fields = ["id", "name"]
    utils.print_list(categories, fields, field_labels)


@utils.arg("id", metavar="<ID>",
           help="ID of a category(s) to show.")
def do_category_show(mc, args):
    """Display category details."""
    category = mc.categories.get(args.id)
    packages = mc.packages.filter(category=category.name)
    to_display = dict(id=category.id,
                      name=category.name,
                      packages=', '.join(p.name for p in packages))
    formatters = {'packages': utils.text_wrap_formatter}
    utils.print_dict(to_display, formatters)


@utils.arg("name", metavar="<CATEGORY_NAME>",
           help="Category name.")
def do_category_create(mc, args):
    """Create a category."""
    category = mc.categories.add({"name": args.name})
    _print_category_list([category])


@utils.arg("id", metavar="<ID>",
           nargs="+", help="ID of a category(ies) to delete.")
def do_category_delete(mc, args):
    """Delete a category."""
    failure_count = 0
    for category_id in args.id:
        try:
            mc.categories.delete(category_id)
        except common_exceptions.HTTPNotFound:
            failure_count += 1
            print("Failed to delete '{0}'; category not found".
                  format(category_id))
    if failure_count == len(args.id):
        raise exceptions.CommandError("Unable to find and delete any of the "
                                      "specified categories.")
    do_category_list(mc)


@utils.arg("class_name", metavar="<CLASS>", help="Class FQN")
@utils.arg("method_names", metavar="<METHOD>", help="Method name", nargs='*')
@utils.arg("--package-name", default=None,
           help="FQN of the package where the class is located")
@utils.arg("--class-version", default='=0',
           help="Class version or version range (version spec)")
def do_class_schema(mc, args):
    """Display class schema"""
    schema = mc.schemas.get(args.class_name, args.method_names,
                            class_version=args.class_version,
                            package_name=args.package_name)
    print(utils.json_formatter(schema.data))
