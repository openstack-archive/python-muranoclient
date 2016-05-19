# Copyright (c) 2015 Mirantis, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from glanceclient.common import utils
from glanceclient import exc
from oslo_utils import encodeutils
import six
from six.moves.urllib import parse

from muranoclient.glance import ArtifactType


glare_urls = {
    'create': '/v{version}/artifacts/{type_name}/v{type_version}/drafts',
    'update_get_delete': '/v{version}/artifacts/{type_name}/v{type_version}'
                         '/{artifact_id}',
    'list_drafts': '/v{version}/artifacts/{type_name}/v{type_version}/drafts?',
    'list_no_drafts': '/v{version}/artifacts/{type_name}/v{type_version}?',
    'publish': '/v{version}/artifacts/{type_name}/v{type_version}/'
               '{artifact_id}/publish',
    'blob': '/v{version}/artifacts/{type_name}/v{type_version}/{artifact_id}'
            '/{blob_property}',
}


class Controller(object):
    def __init__(self, http_client, type_name=None, type_version=None,
                 version='0.1'):
        self.http_client = http_client
        self.type_name = type_name
        self.type_version = type_version
        self.version = version
        self.default_page_size = 20
        self.sort_dir_values = ('asc', 'desc')

    def _check_type_params(self, type_name, type_version):
        """Check that type name and type versions were specified"""
        type_name = type_name or self.type_name
        type_version = type_version or self.type_version

        if type_name is None:
            msg = "Type name must be specified"
            raise exc.HTTPBadRequest(msg)

        if type_version is None:
            msg = "Type version must be specified"
            raise exc.HTTPBadRequest(msg)

        return type_name, type_version

    def _validate_sort_param(self, sort):
        """Validates sorting argument for invalid keys and directions values.

        :param sort: comma-separated list of sort keys with optional <:dir>
        after each key
        """
        for sort_param in sort.strip().split(','):
            key, _sep, dir = sort_param.partition(':')
            if dir and dir not in self.sort_dir_values:
                msg = ('Invalid sort direction: %(sort_dir)s.'
                       ' It must be one of the following: %(available)s.'
                       ) % {'sort_dir': dir,
                            'available': ', '.join(self.sort_dir_values)}
                raise exc.HTTPBadRequest(msg)
        return sort

    def create(self, name, version, type_name=None, type_version=None,
               **kwargs):
        """Create an artifact of given type and version.

        :param name: name of creating artifact.
        :param version: semver string describing an artifact version
        """
        type_name, type_version = self._check_type_params(type_name,
                                                          type_version)
        kwargs.update({'name': name, 'version': version})
        url = glare_urls['create'].format(version=self.version,
                                          type_name=type_name,
                                          type_version=type_version)
        resp, body = self.http_client.post(url, data=kwargs)
        return ArtifactType(**body)

    def update(self, artifact_id, type_name=None, type_version=None,
               remove_props=None, **kwargs):
        """Update attributes of an artifact.

        :param artifact_id: ID of the artifact to modify.
        :param remove_props: List of property names to remove
        :param \*\*kwargs: Artifact attribute names and their new values.
        """
        type_name, type_version = self._check_type_params(type_name,
                                                          type_version)
        url = glare_urls['update_get_delete'].format(version=self.version,
                                                     type_name=type_name,
                                                     type_version=type_version,
                                                     artifact_id=artifact_id)
        hdrs = {
            'Content-Type': 'application/openstack-images-v2.1-json-patch'}

        artifact_obj = self.get(artifact_id, type_name, type_version)

        changes = []
        if remove_props:
            for prop in remove_props:
                if prop in ArtifactType.generic_properties:
                    msg = "Generic properties cannot be removed"
                    raise exc.HTTPBadRequest(msg)
                if prop not in kwargs:
                    changes.append({'op': 'remove',
                                    'path': '/' + prop})

        for prop in kwargs:
            if prop in artifact_obj.generic_properties:
                op = 'add' if getattr(artifact_obj,
                                      prop) is None else 'replace'
            elif prop in artifact_obj.type_specific_properties:
                if artifact_obj.type_specific_properties[prop] is None:
                    op = 'add'
                else:
                    op = 'replace'
            else:
                msg = ("Property '%s' doesn't exist in type '%s' with version"
                       " '%s'" % (prop, type_name, type_version))
                raise exc.HTTPBadRequest(msg)
            changes.append({'op': op, 'path': '/' + prop,
                            'value': kwargs[prop]})

        resp, body = self.http_client.patch(url, headers=hdrs, data=changes)
        return ArtifactType(**body)

    def get(self, artifact_id, type_name=None, type_version=None,
            show_level=None):
        """Get information about an artifact.

        :param artifact_id: ID of the artifact to get.
        :param show_level: value of datalization. Possible values:
                           "none", "basic", "direct", "transitive"
        """
        type_name, type_version = self._check_type_params(type_name,
                                                          type_version)

        url = glare_urls['update_get_delete'].format(version=self.version,
                                                     type_name=type_name,
                                                     type_version=type_version,
                                                     artifact_id=artifact_id)
        if show_level:
            if show_level not in ArtifactType.supported_show_levels:
                msg = "Invalid show level: %s" % show_level
                raise exc.HTTPBadRequest(msg)
            url += '?show_level=%s' % show_level
        resp, body = self.http_client.get(url)
        return ArtifactType(**body)

    def list(self, **kwargs):
        return self._list(drafts=False, **kwargs)

    def drafts(self, **kwargs):
        return self._list(drafts=True, **kwargs)

    def _list(self, drafts, type_name=None, type_version=None, **kwargs):
        """Retrieve a listing of Image objects.

        :param page_size: Number of images to request in each
                          paginated request.
        :returns: generator over list of artifacts.
        """
        type_name, type_version = self._check_type_params(type_name,
                                                          type_version)

        limit = kwargs.get('limit')
        page_size = kwargs.get('page_size') or self.default_page_size

        def paginate(url, page_size, limit=None):
            next_url = url

            while True:
                if limit and page_size > limit:
                    next_url = next_url.replace("limit=%s" % page_size,
                                                "limit=%s" % limit)

                resp, body = self.http_client.get(next_url)
                for artifact in body['artifacts']:
                    yield ArtifactType(**artifact)

                    if limit:
                        limit -= 1
                        if limit <= 0:
                            raise StopIteration

                try:
                    next_url = body['next']
                except KeyError:
                    return

        filters = kwargs.get('filters', {})
        filters['limit'] = page_size

        url_params = []
        for param, items in six.iteritems(filters):
            values = [items] if not isinstance(items, list) else items
            for value in values:
                if isinstance(value, six.string_types):
                    value = encodeutils.safe_encode(value)
                url_params.append({param: value})

        if drafts:
            url = glare_urls['list_drafts'].format(version=self.version,
                                                   type_name=type_name,
                                                   type_version=type_version)
        else:
            url = glare_urls['list_no_drafts'].format(
                version=self.version,
                type_name=type_name,
                type_version=type_version
            )

        for param in url_params:
            url = '%s&%s' % (url, parse.urlencode(param))

        if 'sort' in kwargs:
            url = '%s&sort=%s' % (url, self._validate_sort_param(
                kwargs['sort']))

        for artifact in paginate(url, page_size, limit):
            yield artifact

    def active(self, artifact_id, type_name=None, type_version=None):
        """Set artifact status to 'active'.

        :param artifact_id: ID of the artifact to get.
        """
        type_name, type_version = self._check_type_params(type_name,
                                                          type_version)

        url = glare_urls['publish'].format(version=self.version,
                                           type_name=type_name,
                                           type_version=type_version,
                                           artifact_id=artifact_id)

        resp, body = self.http_client.post(url)
        return ArtifactType(**body)

    def deactivate(self, artifact_id, type_name=None, type_version=None):
        raise NotImplementedError()

    def delete(self, artifact_id, type_name=None, type_version=None):
        """Delete an artifact and all its data.

        :param artifact_id: ID of the artifact to delete.
        """
        type_name, type_version = self._check_type_params(type_name,
                                                          type_version)
        url = glare_urls['update_get_delete'].format(version=self.version,
                                                     type_name=type_name,
                                                     type_version=type_version,
                                                     artifact_id=artifact_id)
        self.http_client.delete(url)

    def upload_blob(self, artifact_id, blob_property, data, position=None,
                    type_name=None, type_version=None):
        """Upload blob data.

        :param artifact_id: ID of the artifact to download a blob
        :param blob_property: blob property name
        :param position: if blob_property is a list then the
        position must be specified
        """
        type_name, type_version = self._check_type_params(type_name,
                                                          type_version)
        hdrs = {'Content-Type': 'application/octet-stream'}

        url = glare_urls['blob'].format(version=self.version,
                                        type_name=type_name,
                                        type_version=type_version,
                                        artifact_id=artifact_id,
                                        blob_property=blob_property)
        if position:
            url += "/%s" % position

        self.http_client.put(url, headers=hdrs, data=data)

    def download_blob(self, artifact_id, blob_property, position=None,
                      type_name=None, type_version=None, do_checksum=True):
        """Get blob data.

        :param artifact_id: ID of the artifact to download a blob
        :param blob_property: blob property name
        :param position: if blob_property is a list then the
        position must be specified
        :param do_checksum: Enable/disable checksum validation.
        """
        type_name, type_version = self._check_type_params(type_name,
                                                          type_version)
        url = glare_urls['blob'].format(version=self.version,
                                        type_name=type_name,
                                        type_version=type_version,
                                        artifact_id=artifact_id,
                                        blob_property=blob_property)
        if position:
            url += '/%s' % position

        url += '/download'

        resp, body = self.http_client.get(url)
        checksum = resp.headers.get('content-md5', None)
        content_length = int(resp.headers.get('content-length', 0))

        if checksum is not None and do_checksum:
            body = utils.integrity_iter(body, checksum)

        return utils.IterableWithLength(body, content_length)

    def delete_blob(self, artifact_id, blob_property, position=None,
                    type_name=None, type_version=None):
        """Delete blob and related data.

        :param artifact_id: ID of the artifact to delete a blob
        :param blob_property: blob property name
        :param position: if blob_property is a list then the
        position must be specified
        """
        type_name, type_version = self._check_type_params(type_name,
                                                          type_version)
        url = glare_urls['blob'].format(version=self.version,
                                        type_name=type_name,
                                        type_version=type_version,
                                        artifact_id=artifact_id,
                                        blob_property=blob_property)
        if position:
            url += '/%s' % position
        self.http_client.delete(url)

    def add_property(self, artifact_id, dependency_id, position=None,
                     type_name=None, type_version=None):
        raise NotImplementedError()

    def replace_property(self, artifact_id, dependency_id, position=None,
                         type_name=None, type_version=None):
        raise NotImplementedError()

    def remove_property(self, artifact_id, dependency_id, position=None,
                        type_name=None, type_version=None):
        raise NotImplementedError()

    def artifact_export(self, artifact_id,
                        type_name=None, type_version=None):
        raise NotImplementedError()

    def artifact_import(self, data, type_name=None, type_version=None):
        raise NotImplementedError()
