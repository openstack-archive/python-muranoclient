#    Copyright (c) 2015 Mirantis, Inc.
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

from six.moves import urllib

from muranoclient.common import base


class Category(base.Resource):
    def __repr__(self):
        return "<Category %s>" % self._info

    def data(self, **kwargs):
        return self.manager.data(self, **kwargs)


class CategoryManager(base.Manager):
    resource_class = Category

    def list(self, **kwargs):
        """Get category list with pagination support.

        :param sort_keys: an array of fields used to sort the list (string)
        :param sort_dir: 'asc' or 'desc' for ascending or descending sort
        :param limit: maximum number of categories to return
        :param marker: begin returning categories that appear later in the
                       category list than that represented by this marker id
        """

        params = {}
        for key, value in kwargs.items():
            if value:
                params[key] = value

        url = '/v1/catalog/categories?{0}'.format(
            urllib.parse.urlencode(params, True))
        return self._list(url, response_key='categories')

    def get(self, id):
        return self._get('/v1/catalog/categories/{0}'.format(id))

    def add(self, data):
        return self._create('/v1/catalog/categories', data)

    def delete(self, id):
        return self._delete('/v1/catalog/categories/{0}'.format(id))
