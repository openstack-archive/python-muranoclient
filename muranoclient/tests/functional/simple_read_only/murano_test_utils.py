# Copyright (c) 2015 Mirantis, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from muranoclient.tests.functional import muranoclient
from tempest_lib.cli import output_parser
import time
import uuid


class CLIUtilsTestBase(muranoclient.ClientTestBase):
    """Basic methods for Murano CLI client."""

    def delete_murano_object(self, murano_object, obj_to_del):
        """Delete Murano object like environment, category
        or environment-template.
        """
        if obj_to_del not in self.listing('{0}-list'.format(murano_object)):
            return
        object_list = self.listing('{0}-delete'.format(murano_object),
                                   params=obj_to_del['ID'])
        start_time = time.time()
        while obj_to_del in self.listing('{0}-list'.format(murano_object)):
            if start_time - time.time() > 60:
                self.fail("{0} is not deleted in 60 seconds".
                          format(murano_object))
        return object_list

    def create_murano_object(self, murano_object, prefix_object_name):
        """Create Murano object like environment, category
        or environment-template.
        """
        object_name = self.generate_name(prefix_object_name)
        mrn_objects = self.listing('{0}-create'.format(murano_object),
                                   params=object_name)
        mrn_object = None
        for obj in mrn_objects:
            if object_name == obj['Name']:
                mrn_object = obj
                break
        if mrn_object is None:
            self.fail("Murano {0} has not been created!".format(murano_object))

        self.addCleanup(self.delete_murano_object, murano_object, mrn_object)
        return mrn_object

    @staticmethod
    def generate_name(prefix):
        """Generate name for objects."""
        suffix = uuid.uuid4().hex[:8]
        return "{0}-{1}".format(prefix, suffix)

    def get_table_struct(self, command, params=""):
        """Get table structure i.e. header of table."""
        return output_parser.table(self.murano(command,
                                               params=params))['headers']

    def get_object(self, object_list, object_value):
        """"Get Murano object by value from list of Murano objects."""
        for obj in object_list:
            if object_value in obj.values():
                return obj
