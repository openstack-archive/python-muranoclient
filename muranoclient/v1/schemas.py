#    Copyright (c) 2016 Mirantis, Inc.
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

import urllib

from muranoclient.common import base


class Schema(base.Resource):
    def __repr__(self):
        return "<Schema %s>" % self._info

    @property
    def data(self):
        return self._info


class SchemaManager(base.Manager):
    resource_class = Schema

    def get(self, class_name, method_names=None,
            class_version=None, package_name=None):
        """Get JSON-schema for class or method"""

        if isinstance(method_names, (list, tuple)):
            method_names = ','.join(method_names)

        base_url = '/v1/schemas/' + '/'.join(
            t for t in (class_name, method_names) if t)

        params = {
            key: value for key, value in (
                ('classVersion', class_version),
                ('packageName', package_name)) if value
        }

        if len(params):
            base_url += '?' + urllib.parse.urlencode(params, True)

        return self._get(base_url)
