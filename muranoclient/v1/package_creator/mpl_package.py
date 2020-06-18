#    Copyright (c) 2014 Mirantis, Inc.
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

import os
import shutil
import tempfile

import yaml

import muranoclient
from muranoclient.apiclient import exceptions
from muranoclient.common import utils


def prepare_package(args):
    """Prepare for application package

    Prepare all files and directories for that application package.
    Generates manifest file and all required parameters for that.

    :param args: list of command line arguments
    :returns: absolute path to directory with prepared files
    """
    if args.type and args.type not in ['Application', 'Library']:
        raise exceptions.CommandError(
            "--type should be set to 'Application' or 'Library'")

    manifest = generate_manifest(args)
    if args.type == 'Application':
        if not args.ui:
            raise exceptions.CommandError("'--ui' is required parameter")
        if not os.path.exists(args.ui) or not os.path.isfile(args.ui):
            raise exceptions.CommandError(
                "{0} is not a file or doesn`t exist".format(args.ui))

    temp_dir = tempfile.mkdtemp()
    manifest_file = os.path.join(temp_dir, 'manifest.yaml')
    classes_directory = os.path.join(temp_dir, 'Classes')
    resource_directory = os.path.join(temp_dir, 'Resources')

    with open(manifest_file, 'w') as f:
        f.write(yaml.dump(manifest, default_flow_style=False))

    logo_file = os.path.join(temp_dir, 'logo.png')
    if not args.logo or (args.logo and not os.path.isfile(args.logo)):
        shutil.copyfile(muranoclient.get_resource('mpl_logo.png'), logo_file)
    else:
        shutil.copyfile(args.logo, logo_file)

    shutil.copytree(args.classes_dir, classes_directory)
    if args.resources_dir:
        if not os.path.isdir(args.resources_dir):
            raise exceptions.CommandError(
                "'--resources-dir' parameter should be a directory")
        shutil.copytree(args.resources_dir, resource_directory)
    if args.ui:
        ui_directory = os.path.join(temp_dir, 'UI')
        os.mkdir(ui_directory)
        shutil.copyfile(args.ui, os.path.join(ui_directory, 'ui.yaml'))
    return temp_dir


def generate_manifest(args):
    """Generates application manifest file.

    If some parameters are missed - they we be generated automatically.
    :param args:
    :returns: dictionary, contains manifest file data
    """
    if not os.path.isdir(args.classes_dir):
        raise exceptions.CommandError(
            "'--classes-dir' parameter should be a directory")
    args = update_args(args)
    if not args.type:
        raise exceptions.CommandError(
            "Too few arguments: --type and --full-name is required")

    if not args.author:
        args.author = args.os_username
    if not args.description:
        args.description = "Description for the application is not provided"

    if not args.full_name:
        raise exceptions.CommandError(
            "Please, provide --full-name parameter")

    manifest = {
        'Format': 'MuranoPL/1.0',
        'Type': args.type,
        'FullName': args.full_name,
        'Name': args.name,
        'Description': args.description,
        'Author': args.author,
        'Classes': args.classes
    }

    if args.tags:
        manifest['Tags'] = args.tags
    return manifest


def update_args(args):
    """Add and update arguments if possible.

    Some parameters are not required and would be guessed
    from muranoPL classes: thus, if class extends system application class
    fully qualified and require names could be calculated.
    Also, in that case type of a package could be set to 'Application'.
    """

    classes = {}
    extends_from_application = False
    for root, dirs, files in os.walk(args.classes_dir):
        for class_file in files:
            class_file_path = os.path.join(root, class_file)
            try:
                with open(class_file_path) as f:
                    content = yaml.load(f, utils.YaqlYamlLoader)

                if not content.get('Name'):
                    raise exceptions.CommandError(
                        "Error in class definition: 'Name' "
                        "section is required")
                class_name = get_fqn_for_name(content.get('Namespaces'),
                                              content['Name'])
                if root == args.classes_dir:
                    relative_path = class_file
                else:
                    relative_path = os.path.join(
                        root.replace(args.classes_dir, "")[1:],
                        class_file)
                classes[class_name] = relative_path

                extends_from_application = check_derived_from_application(
                    content, extends_from_application)
                if extends_from_application:
                    if not args.type:
                        args.type = 'Application'
                    if not args.name:
                        args.name = class_name.split('.')[-1]
                    if not args.full_name:
                        args.full_name = class_name

            except yaml.YAMLError:
                raise exceptions.CommandError(
                    "MuranoPL class {0} should be"
                    " a valid yaml file".format(class_file_path))
            except IOError:
                raise exceptions.CommandError(
                    "Could not open file {0}".format(class_file_path))
    if not classes:
        raise exceptions.CommandError("Application should have "
                                      "at least one class")
    args.classes = classes
    return args


def get_fqn_for_name(namespaces, name):
    """Analyze name for namespace reference.

    If namespaces are used - return a full name
    :param namespaces: content of 'Namespaces' section of muranoPL class
    :param name: name that should be checked
    :returns: generated name according to namespaces
    """
    values = name.split(':')
    if len(values) == 1:
        if '=' in namespaces:
            return namespaces['='] + '.' + values[0]
        return values[0]
    if len(values) > 2:
        raise exceptions.CommandError(
            "Error in class definition: Wrong usage of ':' is "
            "reserved for namespace referencing and could "
            "be used only once "
            "for each name")
    if not namespaces:
        raise exceptions.CommandError(
            "Error in {0} class definition: "
            "'Namespaces' section is missed")

    result = namespaces.get(values[0])
    if not result:
        raise exceptions.CommandError(
            "Error in class definition: namespaces "
            "reference is not correct at the 'Extends'"
            " section")
    return result + '.' + values[1]


def check_derived_from_application(content, extends_from_application):
    """Look up for system 'io.murano.Application' class in extends section"""
    if content.get('Extends'):
        extends = content['Extends']
        if not isinstance(extends, list):
            extends = [extends]

        for name in extends:
            parent_class_name = get_fqn_for_name(
                content.get('Namespaces'),
                name)
            if parent_class_name == 'io.murano.Application':
                if not extends_from_application:
                    return True
                else:
                    raise exceptions.CommandError(
                        "Murano package should have only one class"
                        " extends 'io.murano.Application' class")
    return False
