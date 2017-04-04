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

import collections

from glanceclient import exc as glance_exc
import yaml

from muranoclient.common import exceptions as exc
from muranoclient.common import utils
from muranoclient.i18n import _


def rewrap_http_exceptions(func):
    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except glance_exc.HTTPException as e:
            raise exc.from_code(e.code)
    return inner


class ArtifactRepo(object):
    def __init__(self, client, tenant=None):
        self.tenant = tenant
        self.client = client

    def create(self, fqn, data, **kwargs):

        package = utils.Package.from_file(data)
        manifest = package.manifest
        package_draft = {
            'name': manifest.get('FullName', fqn),
            'version': manifest.get('Version', '0.0.0'),
            'description': manifest.get('Description'),
            'display_name': manifest.get('Name', fqn),
            'type': manifest.get('Type', 'Application'),
            'author': manifest.get('Author'),
            'tags': manifest.get('Tags', []),
            'class_definitions': package.classes.keys()
        }
        for k, v in kwargs.items():
            package_draft[k] = v

        inherits = self._get_local_inheritance(package.classes,
                                               package.resolvers)

        # check for global inheritance
        ancestor_queue = collections.deque(inherits.keys())
        while ancestor_queue:
            ancestor_name = ancestor_queue.popleft()
            child_classes = inherits[ancestor_name]

            ancestors = self.list(class_definitions=ancestor_name)
            for ancestor in ancestors:
                # check if ancestor inherits anything
                ancestor_inherits = \
                    ancestor.type_specific_properties.get('inherits', {})
                for name, value in ancestor_inherits.items():
                    # check if this is the class we actually inherit
                    if ancestor_name in value:
                        ancestor_queue.append(name)
                        inherits[name] = child_classes

        package_draft['inherits'] = inherits

        keywords = self._keywords_from_display_name(
            package_draft['display_name'])
        keywords.extend(package_draft['tags'])
        package_draft['keywords'] = keywords

        # NOTE(ativelkov): this is very racy, but until we have a chance to
        # enforce uniqueness right in glance this is the only way to do it
        visibility = package_draft.get('visibility', 'private')
        if visibility == 'public':
            filters = {}
        else:
            filters = {'owner': self.tenant}
        existing = self.list(name=package_draft['name'],
                             version=package_draft['version'], **filters)
        try:
            next(existing)
            raise exc.HTTPConflict("Package already exists")
        except StopIteration:
            pass

        res = self.client.artifacts.create(**package_draft)
        app_id = res.id
        self.client.artifacts.upload_blob(app_id, 'archive', package.file())
        if package.logo is not None:
            self.client.artifacts.upload_blob(app_id, 'logo', package.logo)
        if package.ui is not None:
            self.client.artifacts.upload_blob(app_id, 'ui_definition',
                                              package.ui)
        package.file().close()
        self.client.artifacts.active(app_id)

        return self.client.artifacts.get(app_id)

    @staticmethod
    def _get_local_inheritance(classes, resolvers):
        result = {}
        for class_name, klass in classes.items():
            if 'Extends' not in klass:
                continue
            ns = klass.get('Namespaces')
            if ns:
                resolver = utils.NamespaceResolver(ns)
            else:
                resolver = resolvers.get(class_name)

            if isinstance(klass['Extends'], list):
                bases = klass['Extends']
            else:
                bases = [klass['Extends']]
            for base_class in bases:
                if resolver:
                    base_fqn = resolver.resolve_name(base_class)
                else:
                    base_fqn = base_class
                result.setdefault(base_fqn, []).append(class_name)
        return result

    @staticmethod
    def _keywords_from_display_name(display_name):
        return display_name.split()[:10]

    def list(self,
             sort_field='name',
             sort_dir='asc',
             type=None,
             tags=None,
             limit=None,
             page_size=None,
             **filters):
        sort = "%s:%s" % (sort_field, sort_dir)
        if type is not None:
            filters['type'] = type
        if tags is not None:
            filters['tag'] = tags
        return self.client.artifacts.list(sort=sort,
                                          limit=limit,
                                          page_size=page_size,
                                          filters=filters)

    def get(self, app_id):
        return self.client.artifacts.get(app_id)

    def delete(self, app_id):
        return self.client.artifacts.delete(app_id)

    def update(self, app_id, props_to_remove=None, **new_props):
        new_keywords = []
        new_name = new_props.get('display_name')
        new_tags = new_props.get('tags')
        if new_name:
            new_keywords.extend(self._keywords_from_display_name(new_name))
        if new_tags:
            new_keywords.extend(new_tags)
        if new_keywords:
            new_props['keywords'] = new_keywords
        visibility = new_props.get('visibility')
        if visibility == 'public':
            package = self.client.artifacts.get(app_id)
            # NOTE(ativelkov): this is very racy, but until we have a chance to
            # enforce uniqueness right in glance this is the only way to do it
            existing = self.list(name=package.name,
                                 version=package.version,
                                 visibility='public')
            try:
                while True:
                    package = next(existing)
                    if package.id == app_id:
                        continue
                    else:
                        raise exc.HTTPConflict("Package already exists")
            except StopIteration:
                pass
        return self.client.artifacts.update(app_id,
                                            remove_props=props_to_remove,
                                            **new_props)

    def toggle_active(self, app_id):
        old_val = self.get(app_id).type_specific_properties['enabled']
        return self.update(app_id, enabled=(not old_val))

    def toggle_public(self, app_id):
        visibility = self.get(app_id).visibility
        if visibility == 'public':
            return self.update(app_id, visibility='private')
        else:
            return self.update(app_id, visibility='public')

    def download(self, app_id):
        return self.client.artifacts.download_blob(app_id, 'archive')

    def get_ui(self, app_id, loader_cls=None):
        ui_stream = "".join(
            self.client.artifacts.download_blob(app_id, 'ui_definition'))
        if loader_cls is None:
            loader_cls = yaml.SafeLoader
        return yaml.load(ui_stream, loader_cls)

    def get_logo(self, app_id):
        return self.client.artifacts.download_blob(app_id, 'logo')


class PackageManagerAdapter(object):
    def __init__(self, legacy, glare):
        self.legacy = legacy
        self.glare = glare

    def categories(self):
        return self.legacy.categories()

    @rewrap_http_exceptions
    def create(self, data, files):
        is_public = data.pop('is_public', None)
        if is_public is not None:
            data['visibility'] = 'public' if is_public else 'private'
        fqn = list(files.keys())[0]
        pkg = self.glare.create(fqn, files[fqn], **data)
        return PackageWrapper(pkg)

    @rewrap_http_exceptions
    def filter(self, **kwargs):
        kwargs.pop('catalog', None)  # NOTE(ativelkov): Glare ignores 'catalog'
        include_disabled = kwargs.pop('include_disabled', False)
        order_by = kwargs.pop('order_by', None)
        search = kwargs.pop('search', None)
        category = kwargs.pop('category', None)
        fqn = kwargs.pop('fqn', None)
        class_name = kwargs.pop('class_name', None)
        name = kwargs.pop('name', None)
        if category:
            kwargs['categories'] = category
        if search:
            kwargs['keywords'] = search
        if order_by:
            kwargs['sort_field'] = order_by
        if not include_disabled:
            kwargs['enabled'] = True
        if fqn:
            kwargs['name'] = fqn
        if class_name:
            kwargs['class_definitions'] = class_name
        if name:
            kwargs['display_name'] = name
        # if 'owned' is used there should be a filter with 'owner' parameter
        if kwargs.pop('owned', None):
            kwargs['owner'] = self.glare.tenant

        for pkg in self.glare.list(**kwargs):
            yield PackageWrapper(pkg)

    @rewrap_http_exceptions
    def list(self, include_disabled=False):
        return self.filter(include_disabled=include_disabled)

    @rewrap_http_exceptions
    def delete(self, app_id):
        return self.glare.delete(app_id)

    @rewrap_http_exceptions
    def get(self, app_id):
        return PackageWrapper(self.glare.get(app_id))

    @rewrap_http_exceptions
    def update(self, app_id, body, operation='replace'):
        is_public = body.pop('is_public', None)
        name = body.pop('name', None)
        if is_public is not None:
            body['visibility'] = 'public' if is_public else 'private'
        if name is not None:
            body['display_name'] = name

        if operation == 'replace':
            return PackageWrapper(self.glare.update(app_id, None, **body))

    @rewrap_http_exceptions
    def toggle_active(self, app_id):
        return self.glare.toggle_active(app_id)

    @rewrap_http_exceptions
    def toggle_public(self, app_id):
        return self.glare.toggle_public(app_id)

    @rewrap_http_exceptions
    def download(self, app_id):
        return "".join(self.glare.download(app_id))

    @rewrap_http_exceptions
    def get_logo(self, app_id):
        return "".join(self.glare.get_logo(app_id))

    @rewrap_http_exceptions
    def get_ui(self, app_id, loader_cls=None):
        return self.legacy.get_ui(app_id, loader_cls)


class PackageWrapper(object):
    def __init__(self, item):
        self._item = item

    @property
    def updated(self):
        return self._item.updated_at

    @property
    def created(self):
        return self._item.created_at

    @property
    def is_public(self):
        return self._item.visibility == 'public'

    @property
    def name(self):
        return self._item.type_specific_properties['display_name']

    @property
    def fully_qualified_name(self):
        return self._item.name

    @property
    def owner_id(self):
        return self._item.owner

    def __getstate__(self):
        return {"item": self._item}

    def __setstate__(self, state):
        self._item = state['item']

    def __getattr__(self, name):
        if name in self._item.type_specific_properties:
            return self._item.type_specific_properties.get(name)
        else:
            return getattr(self._item, name)

    def to_dict(self):
        keys = ('author', 'categories', 'class_definitions', 'created',
                'description', 'enabled', 'fully_qualified_name', 'id',
                'is_public', 'name', 'owner_id', 'tags', 'type',
                'updated')
        missing_keys = [key for key in keys if not hasattr(self, key)]
        if missing_keys:
            raise KeyError(_("Some attributes are missing in "
                             "%(pkg_name)s: %(attrs)s.") %
                           {'pkg_name': self.name,
                            'attrs': ", ".join(missing_keys)})
        return {key: getattr(self, key) for key in keys}
