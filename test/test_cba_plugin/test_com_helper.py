##############################################################################
# COPYRIGHT Ericsson AB 2013
#
# The copyright to the computer program(s) herein is the property of
# Ericsson AB. The programs may be used and/or copied only with written
# permission from Ericsson AB. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

from cbaplugin.com_helper import ComHelper
from cbaplugin.cba_exceptions import CbaHelperException
from cbaplugin.cba_exceptions import ComHelperException
from cbaplugin.cba_exceptions import CBAConfigException
from cbaplugin.cba_exceptions import CompAlreadyInstalledException
import ConfigParser
from StringIO import StringIO

import unittest
import mock

default_config = """
[COM]
rstate=R1A02
com_tar=COM_SDP-<rstate>.tar
com_template_tar=COM_D_TEMPLATE-<rstate>.tar.gz
com_sdp=COM-CXP9017585_3.sdp
com_multi_node_template=ERIC-COM-I1-TEMPLATE-CXP9017585_3-<rstate>.sdp
[COMSA]
rstate=R4C02
"""


class MockCBAConfig(object):
    def __init__(self):
        self.config = ConfigParser.ConfigParser()
        self.config.readfp(StringIO(default_config))

    def read_plugin_config(self, section, option):
        value = self.config.get(section, option)
        return value


def recursive_glob_side_effect(treeroot, pattern):
    return ['/tmpdir']


def campaign_execute_cmd_side_effect(cmd):
    print cmd
    return (0, "Status OK")


def process_config_exception_side_effect():
    raise CBAConfigException("Config Problem")


def post_check_execute_side_effect():
    return [1, ""]


def is_component_installed_ex(hostname, comp_sdp):
    raise CbaHelperException("Problem checking component installed")


def recursive_glob_side_effect1(treeroot, pattern):
    print "rec_glob " + pattern
    if pattern == "file1":
        return ["/var/file1"]
    else:
        return ["/tmp/file2"]


class TestComHelper(unittest.TestCase):

    def setUp(self):
        self.ch = ComHelper(None)
#        self.ch.config = ConfigParser.ConfigParser()
#        self.ch.config.readfp(StringIO(default_config))
        self.ch.config = MockCBAConfig()

#    def test_get_status(self):
#        t_mock = Mock()
#        t_mock.return_value = 1

    @mock.patch('cbaplugin.cba_base_helper.CbaBaseHelper.'
                '_is_component_installed', mock.MagicMock(return_value=False))
    def test_generate_task(self):
        result = self.ch._generate_task(None, None)
        self.assertEqual(result, ("install_sw", "Install COM Software", "COM"),
                        "Unexpected Result from generate_task")

    @mock.patch('cbaplugin.cba_base_helper.CbaBaseHelper.'
                '_is_component_installed', mock.MagicMock(return_value=True))
    def test_generate_task_already_installed(self):
        result = self.ch._generate_task(None, None)
        self.assertEqual(result, ("", "Install COM Software", "COM"),
                        "Unexpected Result from generate_task")

    def test_generate_task_cfg_exception(self):
        cfgmock = mock.Mock(side_effect=process_config_exception_side_effect)
        self.ch._process_config = cfgmock
        self.assertRaises(CBAConfigException,
                          self.ch._generate_task, None, None)

    @mock.patch('cbaplugin.cba_base_helper.CbaBaseHelper.'
                '_is_component_installed',
                mock.MagicMock(side_effect=is_component_installed_ex))
    @mock.patch('cbaplugin.com_helper.ComHelper.install_sw', mock.MagicMock())
    def test_generate_task_component_installed_exception(self):
        self.assertRaises(CbaHelperException,
                          self.ch._generate_task, None, None)
#        self.ch._generate_task(None, None)

    @mock.patch('cbaplugin.com_helper.recursive_glob',
                mock.Mock(side_effect=recursive_glob_side_effect))
    @mock.patch('cbaplugin.file_handler.FileHandler.untar_file',
                mock.MagicMock())
    @mock.patch('cbaplugin.file_handler.FileHandler.clean_sdp_install_dir',
                mock.MagicMock())
    @mock.patch('cbaplugin.campaign_runner.CampaignRunner.'
                'transfer_sdp', mock.MagicMock())
    @mock.patch('cbaplugin.campaign_runner.CampaignRunner.'
                'import_sdp', mock.MagicMock())
    @mock.patch('cbaplugin.campaign_runner.CampaignRunner.'
                'execute_campaign', mock.MagicMock())
    @mock.patch('cbaplugin.cba_base_helper.CbaBaseHelper.'
                '_is_cmw_ready', mock.MagicMock())
    @mock.patch('cbaplugin.campaign_runner.CampaignRunner._execute_cmd',
                mock.MagicMock(side_effect=campaign_execute_cmd_side_effect))
    @mock.patch('cbaplugin.cba_base_helper.CbaBaseHelper.'
                '_is_component_installed', mock.MagicMock(return_value=False))
    def test_do_callback(self):
        self.ch.do_callback(None, "install_sw", "mn1")

#    @mock.patch('cbaplugin.com_helper.recursive_glob',
#                mock.MagicMock(return_value=[""]))
    @mock.patch('cbaplugin.com_helper.recursive_glob',
                mock.Mock(side_effect=recursive_glob_side_effect1))
    def test_get_sdps(self):
#        self.ch.sdp_file_loc.update({"file1": ""})
        self.ch.sdp_file_loc.update({"file2": ""})
        self.ch.sdp_file_loc.update({"file1": ""})
        self.ch._get_sdps()
        self.assertEqual(self.ch.sdp_file_loc["file1"], "/var/", "Incorrect")
        self.assertEqual(self.ch.sdp_file_loc["file2"], "/tmp/", "Incorrect")

    @mock.patch('cbaplugin.com_helper.recursive_glob',
                mock.MagicMock(return_value=[]))
    def test_get_sdps_neg1(self):
#        self.ch.sdp_file_loc.update({"file1": ""})
        self.ch.sdp_file_loc.update({"file1": ""})
        self.assertRaises(ComHelperException, self.ch._get_sdps)

    @mock.patch('cbaplugin.com_helper.recursive_glob',
                mock.MagicMock(return_value=["/var/", "/tmp"]))
    def test_get_sdps_neg2(self):
#        self.ch.sdp_file_loc.update({"file1": ""})
        self.ch.sdp_file_loc.update({"file1": ""})
        self.assertRaises(ComHelperException, self.ch._get_sdps)

    @mock.patch('cbaplugin.cba_base_helper.CbaBaseHelper.'
                '_is_component_installed', mock.MagicMock(return_value=True))
    @mock.patch('cbaplugin.cba_base_helper.CbaBaseHelper.'
                '_is_cmw_ready', mock.MagicMock())
    def test_pre_check(self):
        self.ch.rstate = "R1A"
        self.assertRaises(CompAlreadyInstalledException,
                          self.ch._pre_check, "mn1")

    def test_process_config(self):
        self.ch._process_config()
        print self.ch.sdp_files
        expected_sdps = ['COM-CXP9017585_3.sdp',
                         'ERIC-COM-I1-TEMPLATE-CXP9017585_3-R1A02.sdp']
        expected_sdp_loc = {'COM-CXP9017585_3.sdp': "",
                            'ERIC-COM-I1-TEMPLATE-CXP9017585_3-R1A02.sdp': ""}
        print self.ch.sdp_files
        self.assertEquals(self.ch.sdp_files, expected_sdps,
                          "Sdp files not as expected")
        print self.ch.sdp_file_loc
        self.assertEquals(self.ch.sdp_file_loc, expected_sdp_loc,
                          "Sdp files not as expected")

    @mock.patch('cbaplugin.com_helper.ComHelper._get_sdps',
                mock.MagicMock())
    @mock.patch('cbaplugin.file_handler.FileHandler.clean_sdp_install_dir',
                mock.MagicMock())
    @mock.patch('cbaplugin.file_handler.FileHandler.untar_file',
                mock.MagicMock())
    @mock.patch('cbaplugin.campaign_runner.CampaignRunner')
    @mock.patch('cbaplugin.campaign_runner.CampaignRunner.transfer_sdp',
                mock.MagicMock())
    def test_prepare_for_install_pos(self, mock_cr):
        self.ch.tar_files = ("/tmp/file1", "/tmp/file2")
        self.ch.sdp_files = ("file1.sdp", "file2.sdp")
        self.ch.sdp_file_loc = {"file1.sdp": "/tmp", "file2.sdp": "/var"}
        self.ch._prepare_for_install("mn1")

    @mock.patch('cbaplugin.com_helper.ComHelper._get_sdps',
                mock.MagicMock())
    @mock.patch('cbaplugin.file_handler.FileHandler.clean_sdp_install_dir',
                mock.MagicMock())
    @mock.patch('cbaplugin.campaign_runner.CampaignRunner')
    @mock.patch('cbaplugin.campaign_runner.CampaignRunner.transfer_sdp',
                mock.MagicMock())
    def test_prepare_for_install_neg(self, mock_cr):
        self.ch.tar_files = ("/tmp/file1", "/tmp/file2")
        self.ch.sdp_files = ("file1.sdp", "file2.sdp")
        self.ch.sdp_file_loc = {"file1.sdp": "/tmp", "file2.sdp": "/var"}
        self.assertRaises(IOError, self.ch._prepare_for_install, "mn1")

#    def test_import_campaign(self):
#        pass

#    def test_execute_campaign(self):
#        pass

    @mock.patch('cbaplugin.campaign_runner.CampaignRunner')
    def test_post_check(self, mock_cr):
#        self.ch.campaign.e
        mcr = mock_cr.return_value
        mcr._execute_cmd.return_value = [1, ""]
        self.ch.campaign = mcr
        self.assertRaises(ComHelperException, self.ch._post_check)
