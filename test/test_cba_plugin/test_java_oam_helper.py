##############################################################################
# COPYRIGHT Ericsson AB 2013
#
# The copyright to the computer program(s) herein is the property of
# Ericsson AB. The programs may be used and/or copied only with written
# permission from Ericsson AB. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

import ConfigParser
import unittest
from StringIO import StringIO
import mock

from cbaplugin import cba_config
from cbaplugin.java_oam_helper import JavaOamHelper
from cbaplugin.cba_exceptions import JavaOamHelperException
from cbaplugin.cba_exceptions import CompAlreadyInstalledException
from cbaplugin.cba_exceptions import CompNotInstalledError
#from cbaplugin.cba_exceptions import CBAConfigException
#from cbaplugin.cba_exceptions import FileHandlerException
from cbaplugin.campaign_runner import CampaignRunner

default_config = """
[JAVAOAM]
javaoam_tar=JAVAOAM_RUNTIME_CXP9020490_1_<rstate>.tar.gz
javaoam_template_tar=JAVAOAM_D_TEMPLATE_CXP9020489_1_<rstate>.tar.gz
rstate=R3A18
javaoam_sdps=ERIC-JAVAOAM_CORE-CXP9030376_1-<rstate>.sdp,ERIC-JAVAOAM_LMCLIENT-CXP9030377_1-<rstate>.sdp
javaoam_install_template=ERIC-JAVAOAM-I-2SCxNPL.sdp
javaoam_upgrade_template=ERIC-JAVAOAM-U-2SCxNPL_TEMPLATE.sdp
javaoam_remove_template==ERIC-JAVAOAM-R-2SCxNPL_TEMPLATE.sdp
"""


def pre_gen_side(node_name, comp_sdp):
    return True


def pre_gen_side2(node_name, comp_sdp):
    return False


def comp_installed_side(node, sdp):
    if sdp.startswith("ERIC-JAVAOAM"):
        return False
    else:
        return True


def campaign_execute_cmd_side_effect(cmd):
    print cmd
    return (0, "Status OK")


def recursive_glob_side_effect(treeroot, pattern):
    return ['/tmpdir/test_sdp.sdp']


def recursive_glob_side_effect2(treeroot, pattern):
    return ['/tmpdir/test_sdp.sdp', '/tmpdir/test_sdp2.sdp']


class MockCBAConfig(cba_config.CBAConfig):
    def __init__(self):
        self.config = ConfigParser.ConfigParser()
        self.config.readfp(StringIO(default_config))


class MockCampaignRunner(CampaignRunner):
    pass


class MockJavaOamHelper(JavaOamHelper):
    def __init__(self):
        self.config = MockCBAConfig()
        self.action = "install"
        self.runner = MockCampaignRunner(None, None)
        self.tar_files = []
        self.sdp_files = {}
        self.sdp_dir = "/tmp"
        self.tmp_sdp_dir = "/tmp/cba_sdp"
        self.campaign_name = None


class TestJavaOamHelper(unittest.TestCase):

    def setUp(self):
        self.javaoamhelper = MockJavaOamHelper()

    def test_process_config(self):
        self.javaoamhelper._process_config()
        tarfiles = ["JAVAOAM_RUNTIME_CXP9020490_1_R3A18.tar.gz",
                    "JAVAOAM_D_TEMPLATE_CXP9020489_1_R3A18.tar.gz"]
        self.assertEquals(self.javaoamhelper.tar_files, tarfiles)
        sdpfiles = {'ERIC-JAVAOAM_CORE-CXP9030376_1-R3A18.sdp': '',
                    'ERIC-JAVAOAM_LMCLIENT-CXP9030377_1-R3A18.sdp': '',
                    'ERIC-JAVAOAM-I-2SCxNPL.sdp': ''}
        self.assertEquals(self.javaoamhelper.sdp_files, sdpfiles)
        self.assertEquals(self.javaoamhelper.campaign_name,
                          "ERIC-JAVAOAM-I-2SCxNPL")

    @mock.patch('cbaplugin.java_oam_helper.recursive_glob',
                mock.Mock(side_effect=recursive_glob_side_effect))
    @mock.patch('cbaplugin.java_oam_helper.JavaOamHelper._get_sdps',
                mock.Mock())
    @mock.patch('cbaplugin.file_handler.FileHandler.untar_file',
                mock.MagicMock())
    @mock.patch('cbaplugin.file_handler.FileHandler.clean_sdp_install_dir',
                mock.MagicMock())
    @mock.patch('cbaplugin.campaign_runner.CampaignRunner.transfer_sdp',
                mock.MagicMock())
    @mock.patch('cbaplugin.campaign_runner.CampaignRunner.import_sdp',
                mock.MagicMock())
    @mock.patch('cbaplugin.campaign_runner.CampaignRunner.execute_campaign',
                mock.MagicMock())
    @mock.patch('cbaplugin.cba_base_helper.CbaBaseHelper._is_cmw_ready',
                mock.MagicMock())
    @mock.patch('cbaplugin.cba_base_helper.CbaBaseHelper._import_campaign',
                mock.MagicMock())
    @mock.patch('cbaplugin.campaign_runner.CampaignRunner._execute_cmd',
                mock.MagicMock(side_effect=campaign_execute_cmd_side_effect))
    @mock.patch('cbaplugin.cba_base_helper.CbaBaseHelper.'
                '_is_component_installed',
                mock.MagicMock(side_effect=comp_installed_side))
    def test_do_callback(self):
        self.javaoamhelper.do_callback(None, "install_sw", "mn1")

    @mock.patch('cbaplugin.cba_base_helper.CbaBaseHelper.'
                '_is_component_installed',
                mock.MagicMock(side_effect=pre_gen_side2))
    def test_generate_task(self):
        result = self.javaoamhelper._generate_task(None, None)
        task_method = "install_sw"
        task_description = "Install JavaOaM Component"
        cba_comp = "JAVAOAM"
        self.assertEquals(result, ("install_sw", "Install JavaOaM Software",
                                   "JAVAOAM"))

    @mock.patch('cbaplugin.cba_base_helper.CbaBaseHelper.'
                '_is_component_installed',
                mock.MagicMock(side_effect=pre_gen_side))
    def test_generate_task_neg(self):
        result = self.javaoamhelper._generate_task(None, None)
        task_method = "install_sw"
        task_description = "Install JavaOaM Component"
        cba_comp = "JAVAOAM"
        self.assertEquals(result, ("", "Install JavaOaM Software", "JAVAOAM"))

    def test_get_sdps_neg(self):
        self.javaoamhelper._process_config()
        self.assertRaises(JavaOamHelperException, self.javaoamhelper._get_sdps)

    @mock.patch('cbaplugin.java_oam_helper.recursive_glob',
                mock.Mock(side_effect=recursive_glob_side_effect))
    def test_get_sdps_pos(self):
        self.javaoamhelper._process_config()
        self.javaoamhelper._get_sdps()
        self.assertEquals(self.javaoamhelper.sdp_files.values()[0],
                          '/tmpdir/test_sdp.sdp')

    @mock.patch('cbaplugin.java_oam_helper.recursive_glob',
                mock.Mock(side_effect=recursive_glob_side_effect2))
    def test_get_sdps_neg_multiple_sdps(self):
        self.javaoamhelper._process_config()
        self.assertRaises(JavaOamHelperException, self.javaoamhelper._get_sdps)

    def test_unpack_tarballs_neg(self):
        self.javaoamhelper.tar_files.append("/tmp/test.tar")
        self.assertRaises(IOError, self.javaoamhelper._unpack_tarballs)

    @mock.patch('cbaplugin.file_handler.FileHandler.untar_file',
                mock.MagicMock())
    def test_unpack_tarballs_pos(self):
        self.javaoamhelper.tar_files.append("/tmp/test.tar")
        self.javaoamhelper._unpack_tarballs()

    @mock.patch('cbaplugin.cba_base_helper.CbaBaseHelper.'
                '_is_component_installed',
                mock.MagicMock(side_effect=comp_installed_side))
    @mock.patch('cbaplugin.cba_base_helper.CbaBaseHelper.'
                '_is_cmw_ready', mock.MagicMock())
    def test_pre_check_pos(self):
        self.javaoamhelper._pre_check("mn1")

    @mock.patch('cbaplugin.cba_base_helper.CbaBaseHelper._is_cmw_ready',
                mock.MagicMock())
    def test_pre_check_neg(self):
        def comp_installed_side_javaoam(node, sdp):
            if sdp.startswith("ERIC-JAVAOAM"):
                return True
            else:
                return False

        def comp_installed_side_com(node, sdp):
            if sdp.startswith("ERIC-JAVAOAM"):
                return False
            elif sdp.startswith("ERIC-COM"):
                return False

        def comp_installed_side_comsa(node, sdp):
            if sdp.startswith("ERIC-JAVAOAM"):
                return False
            elif sdp.startswith("ERIC-COM"):
                return True
            elif sdp.startswith("ERIC-ComSa"):
                return False
        tmp_comp_ins = self.javaoamhelper._is_component_installed
        self.javaoamhelper._is_component_installed = \
            comp_installed_side_javaoam
        self.assertRaises(CompAlreadyInstalledException,
                          self.javaoamhelper._pre_check, "mn1")
        self.javaoamhelper._is_component_installed = comp_installed_side_com
        self.assertRaises(CompNotInstalledError, self.javaoamhelper._pre_check,
                          "mn1")
        self.javaoamhelper._is_component_installed = comp_installed_side_comsa
        self.assertRaises(CompNotInstalledError, self.javaoamhelper._pre_check,
                          "mn1")
