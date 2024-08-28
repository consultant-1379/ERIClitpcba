##############################################################################
# COPYRIGHT Ericsson AB 2014
#
# The copyright to the computer program(s) herein is the property of
# Ericsson AB. The programs may be used and/or copied only with written
# permission from Ericsson AB. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

from time import sleep
from os import path

from litp.core.litp_logging import LitpLogger
from cbaplugin.cba_exceptions import CampaignRunnerException
from cmwplugin.execution import execute
from cmwplugin.execution import execute_ms
from cmwplugin.execution import copy
log = LitpLogger()

valid_campaign_status = ["INITIAL", "EXECUTING", "COMPLETED", "COMMITTED"]

SUCCESS = 0
CAMPAIGN_SLEEP_SECONDS = 20


class CampaignRunner(object):
    '''
    CampaignRunner Class is responsible for transferring campaign .sdp
    files to the managed node and execute cmw commands to import and
    execute the campaign
    '''

    def __init__(self, desthost, destpath):
        self.destpath = destpath
        self.desthost = desthost
        self.execute = execute
        self.execute_on_ms = execute_ms
        self.copy = copy

    def _execute_cmd(self, cmd_to_run):
        '''
        calls the method which executes a command on a remote node
        :param cmd_to_run: command to be executed on remote node
        :type  cmd_to_run: string
        '''
        result = self.execute(self.desthost, cmd_to_run)
        retcode = result[0]
        output = result[1]
        return retcode, output

    def transfer_sdp(self, local_path, *filenames):
        '''
        copies the campaign sdp file to remote node and verifies it
        was copied correctly
        :param filenames: list of files to be imported
        :type  filenames: list
        '''
        if not path.exists(local_path):
            log.trace.error("transfer_sdp: Path %s is not valid"
                            % (local_path))
            raise CampaignRunnerException("transfer_sdp :Path %s is not valid"
                                          % (local_path))
        if len(filenames) == 0:
            log.trace.error("transfer_sdp: No files to transfer")
            raise CampaignRunnerException("transfer_sdp: No files to transfer")

        cmd_to_run = "mkdir -p %s" % self.destpath
        result, _ = self._execute_cmd(cmd_to_run)
        if not result == SUCCESS:
            log.trace.error("transfer_sdp: Failed to create %s on the Node"
                            % (self.destpath))
            raise CampaignRunnerException("transfer_sdp: Failed to create %s "
                                          "on the Node" % (self.destpath))
        for filename in filenames:
            log.trace.info("transfer_sdp: Copying file %s" % filename)
            loc_file = local_path + "/" + filename
            result = self.copy(self.desthost, loc_file, self.destpath)
            if not result[0] == SUCCESS:
                log.trace.error("transfer_sdp: Unable to copy %s to %s"
                                % (loc_file, self.desthost))
                raise CampaignRunnerException(
                       "transfer_sdp: Unable to copy %s to %s"
                       % (loc_file, self.desthost))
            cmd_to_run = "md5sum " + loc_file
            result = self.execute_on_ms(cmd_to_run)
            retcode = result[0]
            stdout = result[1]
            if not retcode == SUCCESS:
                log.trace.error(
                       "transfer_sdp: Unexpected result %s on ms for %s "
                       % (str(retcode), cmd_to_run))
                raise CampaignRunnerException(
                       "transfer_sdp: Unexpected result %s on ms for %s "
                       % (str(retcode), cmd_to_run))
            loc_md5 = stdout.split(" ")[0]

            cmd_to_run = "md5sum " + self.destpath + "/" + filename
            result, stdout = self._execute_cmd(cmd_to_run)
            if not result == SUCCESS:
                log.trace.error(
                       "transfer_sdp: Unexpected result %s on node %s for %s "
                       % (str(retcode), self.desthost, cmd_to_run))
                raise CampaignRunnerException(
                       "transfer_sdp: Unexpected result %s on node %s for %s "
                       % (str(retcode), self.desthost, cmd_to_run))
            dest_md5 = stdout.split(" ")[0]
            if not loc_md5 == dest_md5:
                log.trace.error("transfer_sdp: Failed, md5sum does not match")
                raise CampaignRunnerException(
                    "transfer_sdp: Failed, md5sum does not match")

    def import_sdp(self, *filenames):
        '''
        triggers a cmw import of the campaign sdp file
        :param filenames: list of files to be imported
        :type  filenames: list
        '''
        if len(filenames) == 0:
            log.trace.error("import_sdp: No files to import")
            raise CampaignRunnerException("import_sdp: No files to import")

        for filename in filenames:
            log.trace.info("import_sdp: importing %s" % filename)
            cmd_to_run = "cmw-sdp-import " + self.destpath + "/" + filename
            result, _ = self._execute_cmd(cmd_to_run)
            if not result == SUCCESS:
                log.trace.error("import_sdp: Failed to import %s on node %s"
                                % (filename, self.desthost))
                raise CampaignRunnerException("import_sdp: Failed to import %s"
                                              " on node %s"
                                              % (filename, self.desthost))

    def get_campaign_status(self, campaign):
        '''
        retrieves the status of the campaign
        :param campaign: name of CMW campaign
        :type  campaign: string
        '''
        cmd_to_run = "cmw-campaign-status " + campaign
        result, stdout = self._execute_cmd(cmd_to_run)
        if result != SUCCESS:
            log.trace.error("Problem getting campaign status for campaign "
                            " %s: result %s" % (campaign, str(result)))
            raise CampaignRunnerException("Problem getting campaign status "
                                          "for campaign  %s: result %s"
                                          % (campaign, str(result)))
#       expect a result of the form <campaign_name>=<state>
        result_prefix = campaign + "="
        if not stdout.startswith(result_prefix):
            error_str = "get_campaign_status: failed to get valid result for "\
                        "command \"%s\" on node %s. Expected \"%s=<state>\""\
                        " Received \"%s\" "\
                        % (cmd_to_run, self.desthost, campaign, stdout)
            log.trace.error(error_str)
            raise CampaignRunnerException(error_str)
        status = stdout[len(result_prefix):]
        if not status in valid_campaign_status:
            log.trace.error("Unrecognised campaign status: %s for campaign "
                            "%s on node %s"
                            % (status, campaign, self.desthost))
            raise CampaignRunnerException("Unrecognised campaign status: %s "
                                          "for campaign %s on node %s"
                                          % (status, campaign, self.desthost))
        return status

    def start_campaign(self, campaign):
        '''
        starts a campaign on remote node
        :param campaign: name of CMW campaign
        :type  campaign: string
        '''
        log.trace.info("start_campaign: starting %s" % campaign)
        cmd_to_run = "cmw-campaign-start --disable-backup " + campaign
        result, _ = self._execute_cmd(cmd_to_run)
        if not result == SUCCESS:
            log.trace.error("Problem starting campaign %s on node %s"
                            % (campaign, self.desthost))
            raise CampaignRunnerException("Problem starting campaign %s "
                                          "on node %s"
                                          % (campaign, self.desthost))

    def commit_campaign(self, campaign):
        '''
        commits a campaign on remote node
        :param campaign: name of CMW campaign
        :type  campaign: string
        '''
        log.trace.info("commit_campaign: committing %s" % campaign)
        cmd_to_run = "cmw-campaign-commit " + campaign
        result, _ = self._execute_cmd(cmd_to_run)
        if not result == SUCCESS:
            log.trace.error("Problem committing campaign %s on node %s"
                            % (campaign, self.desthost))
            raise CampaignRunnerException("Problem committing campaign %s "
                                          "on node %s"
                                          % (campaign, self.desthost))

    def persist_campaign(self):
        '''
        triggers a cmw configuration persist on remote node
        '''
        log.trace.info("persist_campaign: persisting %s")
        cmd_to_run = "cmw-configuration-persist "
        result, _ = self._execute_cmd(cmd_to_run)
        if not result == SUCCESS:
            log.trace.error("Problem running cmw-configuration-persist"
                            "on node %s" % self.desthost)
            raise CampaignRunnerException("Problem running "
                                "cmw-configuration-persist on node %s"
                                % self.desthost)

    def remove_campaign(self, campaign):
        '''
        triggers a remove of campaign on remote node
        :param campaign: name of CMW campaign
        :type  campaign: string
        '''
        log.trace.info("remove_campaign: removing %s" % campaign)
        cmd_to_run = "cmw-sdp-remove " + campaign
        result, _ = self._execute_cmd(cmd_to_run)
        if not result == SUCCESS:
            log.trace.error("Problem removing campaign %s on node %s"
                            % (campaign, self.desthost))
            raise CampaignRunnerException("Problem removing campaign %s"
                                          "on node %s"
                                          % (campaign, self.desthost))

    def execute_campaign(self, campaign):
        '''
        Verifies that a campaign goes from Initial to Committed
        state
        :param campaign: name of CMW campaign
        :type  campaign: string
        '''
        try:
            log.trace.info("execute_campaign: executing %s on node %s"
                           % (campaign, self.desthost))
            status = self.get_campaign_status(campaign)
            if status == "INITIAL":
                self.start_campaign(campaign)
                status = self.get_campaign_status(campaign)
                while status != "COMPLETED":
                    sleep(CAMPAIGN_SLEEP_SECONDS)
                    status = self.get_campaign_status(campaign)
                self.commit_campaign(campaign)
                while status != "COMMITTED":
                    sleep(CAMPAIGN_SLEEP_SECONDS)
                    status = self.get_campaign_status(campaign)
                self.persist_campaign()
                self.remove_campaign(campaign)
            else:
                log.trace.error("Campaign %s in incorrect state on node %s"
                                % (campaign, self.desthost))
                raise CampaignRunnerException("Campaign %s in incorrect "
                                              "state on node %s"
                                              % (campaign, self.desthost))
        except CampaignRunnerException as ex:
            log.trace.error("execute_campaign: got exception " + str(ex))
            raise ex
