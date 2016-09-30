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

from muranoclient.common import base


class Template(base.Resource):
    """Involves the template resource."""
    def __repr__(self):
        return "<Template %s>" % self._info

    def data(self, **kwargs):
        return self.manager.data(self, **kwargs)


class EnvTemplateManager(base.Manager):
    """Involves the template manager."""
    resource_class = Template

    def list(self):
        """Lists the environment templates."""
        return self._list('/v1/templates', 'templates')

    def create(self, data):
        """Creates a environment template

        :param data: The environment template information.
        """
        return self._create('/v1/templates', data)

    def update(self, env_template_id, name):
        """Updates the environment template name.

        :param env_template_id: The environment template ID.
        :param name: The name to be updated.
        """
        return self._update('/v1/templates/{id}'.format(id=env_template_id),
                            data={'name': name})

    def delete(self, env_template_id):
        """Deletes an environment template name.

        :param env_template_id: The environment template ID.
        """
        return self._delete('/v1/templates/{id}'.format(id=env_template_id))

    def get(self, env_template_id):
        """Gets information about an environment template name.

        :param env_template_id: The environment template ID.
        """
        return self._get("/v1/templates/{id}".format(id=env_template_id))

    def create_app(self, env_template_id, data):
        """Creates an application in an environment template.

        :param env_template_id: The environment template ID.
        :param data: the application information.
        """
        return self.\
            _create('/v1/templates/{id}/services'.
                    format(id=env_template_id), data)

    def delete_app(self, env_template_id, app_id):
        """Deletes an application in an environment template.

        :param env_template_id: The environment template ID.
        :param app_id: the application ID to be deleted.
        """
        return self._delete('/v1/templates/{id}/services/{app_id}'.
                            format(id=env_template_id, app_id=app_id))

    def create_env(self, env_template_id, data):
        """Creates new environment from template.

        :param env_template_id: The environment template ID.
        :param data: The environment information.
        """
        return self._create('/v1/templates/{id}/create-environment'.
                            format(id=env_template_id), data=data)

    def clone(self, env_template_id, name):
        """Clones a public template from one tenant to another.

        :param env_template_id: The environment template ID to be cloned.
        :param name: The name for the new template.
        """
        return self._create('/v1/templates/{id}/clone'.
                            format(id=env_template_id), data={'name': name})
