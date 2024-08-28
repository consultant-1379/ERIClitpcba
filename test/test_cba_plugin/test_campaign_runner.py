##############################################################################
# COPYRIGHT Ericsson AB 2013
#
# The copyright to the computer program(s) herein is the property of
# Ericsson AB. The programs may be used and/or copied only with written
# permission from Ericsson AB. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

from cbaplugin.campaign_runner import CampaignRunner
from cbaplugin.cba_exceptions import CampaignRunnerException

import unittest
from mock import (Mock, MagicMock, patch)

# Name of campaign
campaign = "ERIC-COM-I1-TEMPLATE-CXP9017585_3-R1A02"
host = "managed_node"
destpath = "/root/campaign_files"

first_sdp = "COM-CXP9017585_3.sdp"
second_sdp = "ERIC-COM-I1-TEMPLATE-CXP9017585_3-R1A02.sdp"


class TestCampaignRunner(unittest.TestCase):

    def setUp(self):
        self.runner = CampaignRunner(host, destpath)

    def test_get_status_pos(self):
        stat_mock = Mock(return_value=[0,
             "ERIC-COM-I1-TEMPLATE-CXP9017585_3-R1A02=INITIAL",
             None])

        self.runner.execute = stat_mock

        ans = self.runner.get_campaign_status(campaign)
        self.assertEqual(ans, "INITIAL",
                         "State must be INITIAL, instead got " + ans)

    def test_get_status_neg(self):
        self.runner.execute = Mock(return_value=[1,
            "ERIC-COM-I1-TEMPLATE-CXP9017585_3-R1A02=INITIAL",
            None])
        self.assertRaises(CampaignRunnerException,
                          self.runner.get_campaign_status,
                          campaign)

    @patch('cbaplugin.campaign_runner.sleep', MagicMock())
    def test_execute_campaign_neg(self):
        self.runner.execute = Mock(return_value=[0,
                    "ERIC-COM-I1-TEMPLATE-CXP9017585_3-R1A02=COMPLETED",
                    None])
        self.assertRaises(CampaignRunnerException,
                          self.runner.execute_campaign, campaign)

    @patch('cbaplugin.campaign_runner.sleep', MagicMock())
    def test_execute_campaign_pos(self):
        ret_spec = [
                    [0, "",
                     None],
                    [0, "",
                     None],
                    [0, "ERIC-COM-I1-TEMPLATE-CXP9017585_3-R1A02=COMMITTED",
                     None],
                    [0, "ERIC-COM-I1-TEMPLATE-CXP9017585_3-R1A02=COMPLETED",
                     None],
                    [0, "",
                     None],
                    [0, "ERIC-COM-I1-TEMPLATE-CXP9017585_3-R1A02=COMPLETED",
                     None],
                    [0, "ERIC-COM-I1-TEMPLATE-CXP9017585_3-R1A02=EXECUTING",
                     None],
                    [0, "",
                     None],
                    [0, "ERIC-COM-I1-TEMPLATE-CXP9017585_3-R1A02=INITIAL",
                     None],
                   ]

        # The execute method will be called multiple times during the
        # execute_campaign. This side_effect will pop a different result
        # from the ret_spec list above
        def side_effect(*args, **kwargs):
            print "called with " + str(args)
            result = ret_spec.pop()
            print "Returning   " + str(result)
            return result

        self.runner.execute = Mock(side_effect=side_effect)
        try:
            self.runner.execute_campaign(campaign)
        except CampaignRunnerException as ex:
            self.fail("Got an exception!!!!!!! " + str(ex))

    @patch('os.path.exists', MagicMock())
    def test_transfer_sdp_pos(self):

        self.runner.copy = Mock(return_value=[0, "Fair play", None])
        self.runner.execute_on_ms = Mock(return_value=[0,
                                         "22222333333md5sum something", None])
        self.runner.execute = Mock(return_value=[0,
                                   "22222333333md5sum something", None])
        try:
            self.runner.transfer_sdp("mn", "local_path", "name_of_file")
        except Exception as ex:
            self.fail(str(ex))

    @patch('os.path.exists', MagicMock())
    def test_transfer_sdp_neg1(self):

        self.runner.copy = Mock(return_value=[0, "Fair play", None])
        self.runner.execute_on_ms = Mock(return_value=[0, "", None])
        self.runner.execute = Mock(return_value=[0,
                                   "22222333333md5sum something", None])
        self.assertRaises(CampaignRunnerException, self.runner.transfer_sdp,
                          "local_path", "name_of_file")

    @patch('os.path.exists', MagicMock())
    def test_transfer_sdp_neg2(self):

        self.runner.copy = Mock(return_value=[0, "Fair play", None])
        self.runner.execute_on_ms = Mock(return_value=[1,
                                         "22222333333md5sum something", None])
        self.runner.execute = Mock(return_value=[0,
                                   "22222333333md5sum something", None])
        self.assertRaises(CampaignRunnerException, self.runner.transfer_sdp,
                          "local_path", "name_of_file")

    @patch('os.path.exists', MagicMock())
    def test_transfer_sdp_neg3(self):

        self.runner.copy = Mock(return_value=[0, "Fair play", None])
        self.runner.execute_on_ms = Mock(return_value=[0,
                                         "22222333333md5sum something", None])
        self.runner.execute = Mock(return_value=[1,
                                   "22222333333md5sum something", None])
        self.assertRaises(CampaignRunnerException, self.runner.transfer_sdp,
                          "local_path", "name_of_file")

    # Correct retvalue but invalid md5sum
    @patch('os.path.exists', MagicMock())
    def test_transfer_sdp_neg4(self):

        self.runner.copy = Mock(return_value=[0, "Fair play", None])
        self.runner.execute_on_ms = Mock(return_value=[0,
                                         "22222333333md5sum something", None])
        self.runner.execute = Mock(return_value=[1,
                                   "222333md5sum something", None])
        self.assertRaises(CampaignRunnerException, self.runner.transfer_sdp,
                          "local_path", "name_of_file")

    def test_import_sdp_pos(self):
        # mock for remote md5 sum result
        self.runner.execute = Mock(return_value=[0, "", None])
        try:
            self.runner.import_sdp("name_of_file")
        except Exception as ex:
            self.fail(str(ex))

    def test_import_sdp_neg(self):
        # mock for remote md5 sum result
        self.runner.execute = Mock(return_value=[1, "", None])
        self.assertRaises(CampaignRunnerException, self.runner.import_sdp,
                          "FileName")

    def test_start_campaign_pos(self):
        self.runner.execute = Mock(return_value=[0, "", None])
        try:
            self.runner.start_campaign("Campaign1")
        except Exception as ex:
            self.fail(str(ex))

    def test_start_campaign_neg(self):
        self.runner.execute = Mock(return_value=[1, "", None])
        self.assertRaises(CampaignRunnerException, self.runner.start_campaign,
                          campaign)

    def test_commit_campaign_pos(self):
        self.runner.execute = Mock(return_value=[0, "", None])
        self.runner.commit_campaign("Campaign1")

    def test_commit_campaign_neg(self):
        self.runner.execute = Mock(return_value=[1, "", None])
        self.assertRaises(CampaignRunnerException, self.runner.commit_campaign,
                          campaign)

    def test_persist_campaign_pos(self):
        self.runner.execute = Mock(return_value=[0, "", None])
        self.runner.persist_campaign()

    def test_persist_campaign_neg(self):
        self.runner.execute = Mock(return_value=[1, "", None])
        self.assertRaises(CampaignRunnerException,
                          self.runner.persist_campaign)

    def test_remove_campaign_pos(self):
        self.runner.execute = Mock(return_value=[0, "", None])
        self.runner.commit_campaign("Campaign1")

    def test_remove_campaign_neg(self):
        self.runner.execute = Mock(return_value=[1, "", None])
        self.assertRaises(CampaignRunnerException, self.runner.commit_campaign,
                          campaign)
