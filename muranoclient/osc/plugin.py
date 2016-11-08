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

"""OpenStackClient plugin for Application Catalog service."""

from osc_lib import utils
from oslo_log import log as logging

from muranoclient.apiclient import exceptions as exc
from muranoclient.glance import client as art_client
from muranoclient.i18n import _

LOG = logging.getLogger(__name__)

DEFAULT_APPLICATION_CATALOG_API_VERSION = "1"
API_VERSION_OPTION = "os_application_catalog_api_version"
API_NAME = "application_catalog"
API_VERSIONS = {
    '1': 'muranoclient.v1.client.Client',
}


def make_client(instance):
    """Returns an application-catalog service client"""
    application_catalog_client = utils.get_client_class(
        API_NAME,
        instance._api_version[API_NAME],
        API_VERSIONS)
    LOG.debug("Instantiating application-catalog client: {0}".format(
              application_catalog_client))

    kwargs = {
        'session': instance.session,
        'service_type': 'application-catalog',
        'region_name': instance._region_name
    }

    murano_packages_service = \
        instance.get_configuration().get('murano_packages_service')

    if murano_packages_service == 'glare':
        glare_endpoint = instance.get_configuration().get('glare_url')
        if not glare_endpoint:
            try:
                # no glare_endpoint and we requested to store packages in glare
                # check keystone catalog
                glare_endpoint = instance.get_endpoint_for_service_type(
                    'artifact',
                    region_name=instance._region_name,
                    interface=instance._interface
                )
            except Exception:
                raise exc.CommandError(
                    "You set murano-packages-service to {}"
                    " but there is not 'artifact' endpoint in keystone"
                    " Either register one or specify endpoint "
                    " via either --glare-url or env[GLARE_API]".format(
                        murano_packages_service))

        artifacts_client = art_client.Client(
            endpoint=glare_endpoint,
            type_name='murano',
            type_version=1,
            token=instance.auth_ref.auth_token)
        kwargs['artifacts_client'] = artifacts_client

    murano_endpoint = instance.get_configuration().get('murano_url')
    if not murano_endpoint:
        murano_endpoint = instance.get_endpoint_for_service_type(
            'application-catalog',
            region_name=instance._region_name,
            interface=instance._interface
        )

    client = application_catalog_client(murano_endpoint, **kwargs)
    return client


def build_option_parser(parser):
    """Hook to add global options"""
    parser.add_argument(
        '--os-application-catalog-api-version',
        metavar='<application-catalog-api-version>',
        default=utils.env(
            'OS_APPLICATION_CATALOG_API_VERSION',
            default=DEFAULT_APPLICATION_CATALOG_API_VERSION),
        help=_("Application catalog API version, default={0}"
               "(Env:OS_APPLICATION_CATALOG_API_VERSION)").format(
                   DEFAULT_APPLICATION_CATALOG_API_VERSION))
    parser.add_argument('--murano-url',
                        default=utils.env('MURANO_URL'),
                        help=_('Defaults to env[MURANO_URL].'))
    parser.add_argument('--glare-url',
                        default=utils.env('GLARE_URL'),
                        help='Defaults to env[GLARE_URL].')
    parser.add_argument('--murano-packages-service',
                        choices=['murano', 'glare'],
                        default=utils.env('MURANO_PACKAGES_SERVICE',
                                          default='murano'),
                        help='Specifies if murano-api ("murano") or '
                             'Glance Artifact Repository ("glare") '
                             'should be used to store murano packages. '
                             'Defaults to env[MURANO_PACKAGES_SERVICE] or '
                             'to "murano"')
    return parser
