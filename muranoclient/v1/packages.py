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

from oslo_serialization import jsonutils
import six
from six.moves import urllib
import yaml

from muranoclient.common import base
from muranoclient.common import exceptions
from muranoclient.common import utils

DEFAULT_PAGE_SIZE = 20


class Package(base.Resource):
    def __repr__(self):
        return "<Package %s>" % self._info

    def data(self, **kwargs):
        return self.manager.data(self, **kwargs)


class PackageManager(base.Manager):
    resource_class = Package
    _tracked_packages = set()

    def create(self, data, files):
        for pkg_file in files.values():
            utils.Package.from_file(pkg_file)
            pkg_file.seek(0)

        response = self.api.request(
            '/v1/catalog/packages',
            'POST',
            data={'__metadata__': jsonutils.dumps(data)},
            files=files
        )
        if not response.ok:
            setattr(response, 'status', response.status_code)
            raise exceptions.from_response(response)
        body = jsonutils.loads(response.text)
        return self.resource_class(self, body)

    def get(self, app_id):
        return self._get('/v1/catalog/packages/{0}'.format(app_id))

    def filter(self, **kwargs):

        def construct_url(params):
            for k, v in params.items():
                if isinstance(v, six.text_type):
                    v = v.encode('utf-8')
                    params[k] = v
            return '?'.join(
                ['/v1/catalog/packages',
                 urllib.parse.urlencode(params, doseq=True)]
            )

        def paginate(_url):
            # code from Glance
            resp, body = self.api.json_request(_url, 'GET')
            for package in body['packages']:
                yield package
            try:
                m_kwargs = kwargs.copy()
                m_kwargs['marker'] = body['next_marker']
                next_url = construct_url(m_kwargs)
            except KeyError:
                return
            else:
                for package in paginate(next_url):
                    yield package

        if 'page_size' not in kwargs:
            kwargs['limit'] = kwargs.get('limit', DEFAULT_PAGE_SIZE)
        else:
            kwargs['limit'] = kwargs['page_size']

        url = construct_url(kwargs)

        for package in paginate(url):
            yield self.resource_class(self, package, loaded=True)

    def list(self, include_disabled=False, limit=20):
        return self.filter(include_disabled=include_disabled, limit=limit)

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
        for key, value in body.items():
            data.append({'op': operation, 'path': '/' + key, 'value': value})
        return self.api.json_patch_request(url, data=data)

    def download(self, app_id):
        url = '/v1/catalog/packages/{0}/download'.format(app_id)
        response = self.api.request(url, 'GET', log=False)
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
            loader_cls = yaml.SafeLoader

        url = '/v1/catalog/packages/{0}/ui'.format(app_id)
        response = self.api.request(url, 'GET')
        if response.status_code == 200:
            return yaml.load(response.content, loader_cls)
        else:
            raise exceptions.from_response(response)

    def get_logo(self, app_id):
        url = '/v1/catalog/packages/{0}/logo'.format(app_id)
        response = self.api.request(url, 'GET')
        if response.status_code == 200:
            return response.content
        else:
            raise exceptions.from_response(response)

    def get_supplier_logo(self, app_id):
        url = '/v1/catalog/packages/{0}/supplier_logo'.format(app_id)
        response = self.api.request(url, 'GET')
        if response.status_code == 200:
            return response.content
        else:
            raise exceptions.from_response(response)
