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

import urllib

from oslo.serialization import jsonutils
import yaml

from muranoclient.common import base
from muranoclient.common import exceptions

DEFAULT_PAGE_SIZE = 20


class Package(base.Resource):
    def __repr__(self):
        return "<Package %s>" % self._info

    def data(self, **kwargs):
        return self.manager.data(self, **kwargs)


class Category(base.Resource):
    def __init__(self, manager, info, loaded=False):
        self.value = info

    def __unicode__(self):
        return self.value

    def __repr__(self):
        return self.value


class PackageManager(base.Manager):
    resource_class = Package

    def categories(self):
        return self._list('/v1/catalog/packages/categories',
                          response_key='categories', obj_class=Category)

    def create(self, data, files):
        response, body = self.api.raw_request(
            'POST',
            '/v1/catalog/packages',
            body=data,
            files=files,
        )
        if not response.ok:
            setattr(response, 'status', response.status_code)
            raise exceptions.from_response(response)
        body = jsonutils.loads(response.text)
        return self.resource_class(self, body)

    def get(self, app_id):
        return self._get('/v1/catalog/packages/{0}'.format(app_id))

    def filter(self, **kwargs):
        def paginate(_url):
            # code from Glance
            resp, body = self.api.json_request('GET', _url)
            for image in body['packages']:
                yield image
            try:
                next_url = body['next_marker']
            except KeyError:
                return
            else:
                for image in paginate(next_url):
                    yield image

        if 'page_size' not in kwargs:
            kwargs['limit'] = DEFAULT_PAGE_SIZE
        else:
            kwargs['limit'] = kwargs['page_size']

        query_str = urllib.urlencode(kwargs, doseq=True)
        url = '?'.join(['/v1/catalog/packages', query_str])

        for package in paginate(url):
            yield self.resource_class(self, package, loaded=True)

    def list(self, include_disabled=False):
        return self.filter(include_disabled=include_disabled)

    def delete(self, app_id):
        return self._delete('/v1/catalog/packages/{0}'.format(app_id))

    def update(self, app_id, body, operation='replace'):
        """Translates dictionary to jsonpatch request

        :param app_id: string, id of updating application
        :param body: dictionary, mapping between keys and values for update
        :param operation: string, way of updating: replace, remove, add

        :returns: HTTP response
        """
        url = '/v1/catalog/packages/{0}'.format(app_id)
        data = []
        for key, value in body.iteritems():
            data.append({'op': operation, 'path': '/' + key, 'value': value})
        return self.api.json_patch_request(url, data=data)

    def download(self, app_id):
        url = '/v1/catalog/packages/{0}/download'.format(app_id)
        response = self.api.raw_request('GET', url)
        if response.status_code == 200:
            return response.content
        else:
            raise exceptions.from_response(response)

    def toggle_active(self, app_id):
        url = '/v1/catalog/packages/{0}'.format(app_id)
        enabled = self.get(app_id).enabled
        data = [{'op': 'replace', 'path': '/enabled', 'value': not enabled}]
        return self.api.json_patch_request(url, data=data)

    def toggle_public(self, app_id):
        url = '/v1/catalog/packages/{0}'.format(app_id)
        is_public = self.get(app_id).is_public
        data = [{'op': 'replace', 'path': '/is_public',
                'value': not is_public}]
        return self.api.json_patch_request(url, body=data)

    def get_ui(self, app_id, loader_cls=None):
        if loader_cls is None:
            loader_cls = yaml.Loader

        url = '/v1/catalog/packages/{0}/ui'.format(app_id)
        response = self.api.raw_request('GET', url)
        if response.status_code == 200:
            return yaml.load(response.content, loader_cls)
        else:
            raise exceptions.from_response(response)

    def get_logo(self, app_id):
        url = '/v1/catalog/packages/{0}/logo'.format(app_id)
        response = self.api.raw_request('GET', url)
        if response.status_code == 200:
            return response.content
        else:
            raise exceptions.from_response(response)

    def get_supplier_logo(self, app_id):
        url = '/v1/catalog/packages/{0}/supplier_logo'.format(app_id)
        response = self.api.raw_request('GET', url)
        if response.status_code == 200:
            return response.content
        else:
            raise exceptions.from_response(response)
