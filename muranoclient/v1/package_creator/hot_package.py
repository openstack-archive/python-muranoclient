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
from muranoclient.openstack.common.apiclient import exceptions


def generate_manifest(args):
    """Generates application manifest file.
    If some parameters are missed - they we be generated automatically.
    :param args:

    :returns: dictionary, contains manifest file data

    """
    if not os.path.isfile(args.template):
        raise exceptions.CommandError(
            "Template '{0}' doesn`t exist".format(args.template))
    filename = os.path.basename(args.template)
    if not args.name:
        args.name = os.path.splitext(filename)[0]
    if not args.full_name:
        prefix = 'io.murano.apps.generated'
        normalized_name = args.name.replace('_', ' ').replace('-', ' ')
        normalized_name = normalized_name.title().replace(' ', '')
        args.full_name = '{0}.{1}'.format(prefix, normalized_name)
    try:
        with open(args.template, 'rb') as heat_file:
            yaml_content = yaml.load(heat_file)
            if not args.description:
                args.description = yaml_content.get(
                    'description',
                    'Heat-defined application for a template "{0}"'.format(
                        filename))
    except yaml.YAMLError:
        raise exceptions.CommandError(
            "Heat template, represented by --'template' parameter"
            " should be a valid yaml file")
    if not args.author:
        args.author = args.os_username
    if not args.tags:
        args.tags = ['Heat-generated']

    manifest = {
        'Format': 'Heat.HOT/1.0',
        'Type': 'Application',
        'FullName': args.full_name,
        'Name': args.name,
        'Description': args.description,
        'Author': args.author,
        'Tags': args.tags
    }
    return manifest


def prepare_package(args):
    """Compose required files for murano application package.
    :param args: list of command line arguments

    :returns: absolute path to directory with prepared files
    """
    manifest = generate_manifest(args)

    temp_dir = tempfile.mkdtemp()
    manifest_file = os.path.join(temp_dir, 'manifest.yaml')
    template_file = os.path.join(temp_dir, 'template.yaml')

    logo_file = os.path.join(temp_dir, 'logo.png')
    if not args.logo:
        shutil.copyfile(muranoclient.get_resource('heat_logo.png'), logo_file)
    else:
        if os.path.isfile(args.logo):
            shutil.copyfile(args.logo, logo_file)

    with open(manifest_file, 'w') as f:
        f.write(yaml.dump(manifest, default_flow_style=False))
    shutil.copyfile(args.template, template_file)

    return temp_dir
