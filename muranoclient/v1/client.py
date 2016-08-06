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

from muranoclient.common import http
from muranoclient.v1 import actions
from muranoclient.v1 import artifact_packages
from muranoclient.v1 import categories
from muranoclient.v1 import deployments
from muranoclient.v1 import environments
from muranoclient.v1 import instance_statistics
from muranoclient.v1 import packages
from muranoclient.v1 import request_statistics
from muranoclient.v1 import schemas
from muranoclient.v1 import services
from muranoclient.v1 import sessions
from muranoclient.v1 import static_actions
from muranoclient.v1 import templates


class Client(object):
    """Client for the Murano v1 API.

    :param string endpoint: A user-supplied endpoint URL for the service.
    :param string token: Token for authentication.
    :param integer timeout: Allows customization of the timeout for client
                            http requests. (optional)
    """

    def __init__(self, *args, **kwargs):
        """Initialize a new client for the Murano v1 API."""
        self.glance_client = kwargs.pop('glance_client', None)
        tenant = kwargs.pop('tenant', None)
        artifacts_client = kwargs.pop('artifacts_client', None)
        self.http_client = http._construct_http_client(*args, **kwargs)
        self.environments = environments.EnvironmentManager(self.http_client)
        self.env_templates = templates.EnvTemplateManager(self.http_client)
        self.sessions = sessions.SessionManager(self.http_client)
        self.services = services.ServiceManager(self.http_client)
        self.deployments = deployments.DeploymentManager(self.http_client)
        self.schemas = schemas.SchemaManager(self.http_client)
        self.request_statistics = \
            request_statistics.RequestStatisticsManager(self.http_client)
        self.instance_statistics = \
            instance_statistics.InstanceStatisticsManager(self.http_client)
        pkg_mgr = packages.PackageManager(self.http_client)
        if artifacts_client:
            artifact_repo = artifact_packages.ArtifactRepo(artifacts_client,
                                                           tenant)
            self.packages = artifact_packages.PackageManagerAdapter(
                pkg_mgr, artifact_repo)
        else:
            self.packages = pkg_mgr
        self.actions = actions.ActionManager(self.http_client)
        self.static_actions = static_actions.StaticActionManager(
            self.http_client)
        self.categories = categories.CategoryManager(self.http_client)
