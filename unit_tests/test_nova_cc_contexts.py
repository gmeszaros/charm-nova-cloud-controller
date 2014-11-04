from __future__ import print_function

import mock
import nova_cc_context as context

from charmhelpers.contrib.openstack import utils

from test_utils import CharmTestCase


TO_PATCH = [
    'apt_install',
    'filter_installed_packages',
    'relation_ids',
    'relation_get',
    'related_units',
    'log',
    'unit_get',
    'relations_for_id',
]


def fake_log(msg, level=None):
    level = level or 'INFO'
    print('[juju test log (%s)] %s' % (level, msg))


class NovaComputeContextTests(CharmTestCase):
    def setUp(self):
        super(NovaComputeContextTests, self).setUp(context, TO_PATCH)
        self.relation_get.side_effect = self.test_relation.get
        self.log.side_effect = fake_log

    @mock.patch.object(utils, 'os_release')
    def test_instance_console_context_without_memcache(self, os_release):
        self.unit_get.return_value = '127.0.0.1'
        self.relation_ids.return_value = 'cache:0'
        self.related_units.return_value = 'memcached/0'
        instance_console = context.InstanceConsoleContext()
        os_release.return_value = 'icehouse'
        self.assertEqual({'memcached_servers': []},
                         instance_console())

    @mock.patch.object(utils, 'os_release')
    def test_instance_console_context_with_memcache(self, os_release):
        memcached_servers = [{'private-address': '127.0.1.1',
                              'port': '11211'}]
        self.unit_get.return_value = '127.0.0.1'
        self.relation_ids.return_value = ['cache:0']
        self.relations_for_id.return_value = memcached_servers
        self.related_units.return_value = 'memcached/0'
        instance_console = context.InstanceConsoleContext()
        os_release.return_value = 'icehouse'
        self.maxDiff = None
        self.assertEqual({'memcached_servers': memcached_servers},
                         instance_console())
