##############################################################################
# COPYRIGHT Ericsson AB 2013
#
# The copyright to the computer program(s) herein is the property of
# Ericsson AB. The programs may be used and/or copied only with written
# permission from Ericsson AB. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

from cbaplugin.cba_base_helper import CbaBaseHelper
from cbaplugin.cba_exceptions import CbaHelperException
from cbaplugin.cba_exceptions import CMWStateError
from cbaplugin.cba_exceptions import CommandExecutionError

from litp.extensions.core_extension import CoreExtension
from litp.core.execution_manager import ExecutionManager
from litp.core.model_manager import ModelManager
from litp.core.plugin_manager import PluginManager
from litp.core.puppet_manager import PuppetManager
from litp.core.model_type import ItemType, Child

import unittest
import sys


class MockPlugin(object):
    def cba_callback_method(self,
                            callback_api,
                            method_name,
                            cba_component,
                            *args,
                            **kwargs):
        pass

class MockHelperClass(object):
    def create_configuration(self, plugin_api_context, cluster):
        return []

    @staticmethod
    def do_callback(callback_api, method_name, *args, **kwargs):
        pass

class MockCallbackApiObject(object):
    pass

class MockApiContext(object):
    pass

class MockCluster(object):
    services = MockPlugin()
    def query(self, item):
        if item == 'node':
            return [MockNode()]
        return []

class MockNode(object):
    hostname = 'mn1'
    node_id = '1'

class MockRunner(object):
    def transfer_sdp(self, path, sdp_name):
        pass
    def import_sdp(self, sdp_name):
        pass
    def execute_campaign(self, campaign_name):
        pass

class MockSdpFiles(object):
    def items(self):
        return [('sdp_name', 'sdp_path')]

class TestCbaBaseHelper(unittest.TestCase):

    def test_create_configuration(self):
        def _mock_generate_task(plugin_api_context, hostname):
            return 'mock_method', 'Mock desc', 'Mock_Comp'
        def _create_callback_task(mi, td, cm, cc, pnn):
            return []
        def _mock_determine_primary_node(cluster):
            return MockNode()
        cbh = CbaBaseHelper(MockPlugin)
        plugin_api_context = MockApiContext()
        cluster = MockCluster()
        cbh._generate_task = _mock_generate_task
        cbh._determine_primary_node = _mock_determine_primary_node
        cbh.create_configuration(plugin_api_context, cluster)

    def test_create_configuration__no_taak(self):
        def _mock_generate_task(plugin_api_context, hostname):
            return '', 'Mock desc', 'Mock_Comp'
        def _create_callback_task(mi, td, cm, cc, pnn):
            return []
        def _mock_determine_primary_node(cluster):
            return MockNode()
        cbh = CbaBaseHelper(MockPlugin)
        plugin_api_context = MockApiContext()
        cluster = MockCluster()
        cbh._generate_task = _mock_generate_task
        cbh._determine_primary_node = _mock_determine_primary_node
        cbh.create_configuration(plugin_api_context, cluster)

    def test_determine_primary_node(self):
        cbh = CbaBaseHelper(MockPlugin)
        cbh._determine_primary_node(MockCluster())

    def test_generate_task(self):
        cbh = CbaBaseHelper(MockPlugin)
        cbh._generate_task(MockApiContext(), 'mn1')

    def test_do_callback(self):
        cbh = CbaBaseHelper(MockPlugin)
        cbh.do_callback(MockApiContext(), 'test')

    def test_install_sw(self):
        def _mock_execute(hostname, cmd):
            return 0, '', ''
        def _mock_get_camp_runner(node_hostname, camp_dir):
            return MockRunner()
        cbh = CbaBaseHelper(MockPlugin)
        cbh._get_camp_runner = _mock_get_camp_runner
        cbh._execute = _mock_execute
        cbh.install_sw(MockCallbackApiObject, 'mn1')

    def test_upgrade_sw(self):
        cbh = CbaBaseHelper(MockPlugin)
        cbh.upgrade_sw(MockCallbackApiObject, 'mn1')

    def test_import_campaign(self):
        def _mock_execute(hostname, cmd):
            return 0, '', ''
        def _mock_get_camp_runner(node_hostname, camp_dir):
            return MockRunner()
        cbh = CbaBaseHelper(MockPlugin)
        cbh._execute = _mock_execute
        cbh.sdp_files = MockSdpFiles()
        cbh._get_camp_runner = _mock_get_camp_runner
        cbh._import_campaign('hostname')

    def test_import_campaign__with_non_zero(self):
        def _mock_execute(hostname, cmd):
            return 1, '', ''
        cbh = CbaBaseHelper(MockPlugin)
        cbh._execute = _mock_execute
        try:
            cbh._import_campaign('hostname')
        except CbaHelperException:
            pass

    def test_execute(self):
        cbh = CbaBaseHelper(MockPlugin)
        cbh._execute('', 'ls')

    def test_get_camp_runner(self):
        cbh = CbaBaseHelper(MockPlugin)
        cbh._get_camp_runner('mn1', '/tmp')

    def test_is_cmw_ready(self):
        cbh = CbaBaseHelper(MockPlugin)
        def _mock_execute(hostname, cmd):
            return 0, 'Status OK', ''
        cbh._execute = _mock_execute
        cbh._is_cmw_ready('mn1')

    def test_is_cmw_ready_err1(self):
        cbh = CbaBaseHelper(MockPlugin)
        def _mock_execute(hostname, cmd):
            return 1, 'Status OK', ''
        cbh._execute = _mock_execute
        try:
            cbh._is_cmw_ready('mn1')
        except CMWStateError:
            pass

    def test_is_cmw_ready_err2(self):
        cbh = CbaBaseHelper(MockPlugin)
        def _mock_execute(hostname, cmd):
            return 0, 'Status NOT OK', ''
        cbh._execute = _mock_execute
        try:
            cbh._is_cmw_ready('mn1')
        except CMWStateError:
            pass

    def test_is_component_installed(self):
        cbh = CbaBaseHelper(MockPlugin)
        def _mock_execute(hostname, cmd):
            return 0, 'Used', ''
        cbh._execute = _mock_execute
        cbh._is_component_installed('mn1', 'SDP')

    def test_is_component_installed_err1(self):
        cbh = CbaBaseHelper(MockPlugin)
        def _mock_execute(hostname, cmd):
            return 1, 'Used', ''
        cbh._execute = _mock_execute
        try:
            cbh._is_component_installed('mn1', 'SDP')
        except CommandExecutionError:
            pass

    def test_is_component_installed_err2(self):
        cbh = CbaBaseHelper(MockPlugin)
        def _mock_execute(hostname, cmd):
            return 0, 'Not Used', ''
        cbh._execute = _mock_execute
        try:
            cbh._is_component_installed('mn1', 'SDP')
        except CbaHelperException:
            pass

if __name__ == "__main__":
    unittest.main()
