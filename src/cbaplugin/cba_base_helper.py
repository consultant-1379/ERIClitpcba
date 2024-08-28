##############################################################################
# COPYRIGHT Ericsson AB 2013
#
# The copyright to the computer program(s) herein is the property of
# Ericsson AB. The programs may be used and/or copied only with written
# permission from Ericsson AB. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

import os

from litp.core.execution_manager import CallbackTask
from cmwplugin.execution import execute
from cbaplugin.campaign_runner import CampaignRunner
from cbaplugin.cba_exceptions import CbaHelperException
from cbaplugin.cba_exceptions import CMWStateError
from litp.core.litp_logging import LitpLogger
from cbaplugin import cba_constants
log = LitpLogger()


class CbaBaseHelper(object):

    def __init__(self, plugin):
        self.plugin = plugin
        self.runner = None
        self.sdp_files = {}
        self.campaign_name = None
        self.tmp_sdp_dir = cba_constants.CBA_SDP_TMPDIR

    ### Generate Task ###
    def create_configuration(self, plugin_api_context, cluster):
        tasks = []
        model_item = cluster.services
        primary_node_name = self._determine_primary_node(cluster)
        task_method, task_description, cba_comp = \
                                self._generate_task(plugin_api_context,
                                                    primary_node_name)
        if task_method == '':
            return tasks
        tasks.append(CallbackTask(model_item,
                                  task_description,
                                  self.plugin().cba_callback_method,
                                  task_method,
                                  cba_comp,
                                  primary_node_name)
        )
        return tasks

    def _generate_task(self, plugin_api_context, primary_node_name):
        '''
        @summary: This method should be overridden by the Helper Class method
        '''
        pass

    def do_callback(self, callback_api, method_name, *args, **kwargs):
        '''
        @summary: This method should be overridden by the Helper Class method
                  if method_name == 'install_sw':
                      self.install_sw(callback_api, *args, **kwargs)
        '''
        pass

    #### Install Task ###
    def install_sw(self, _, node_hostname):
        '''
        '''
        self._pre_check(node_hostname)
        self._prepare_for_install(node_hostname)
        self._import_campaign(node_hostname)
        self._execute_campaign(node_hostname)
        self._post_check()

    def _pre_check(self, node_hostname):
        '''
        Method should be overridden
        '''
        pass

    def _prepare_for_install(self, node_name):
        '''
        Method should be overridden
        '''
        pass

    def _import_campaign(self, node_hostname):
        '''
        Method should be overridden
        '''
        self._clean_up(node_hostname)
        rc, _, stderr = self._execute(node_hostname,
                                           "mkdir -p %s" % self.tmp_sdp_dir)
        if rc != 0:
            log.trace.error("Failed to create dir %s: %s" % (self.tmp_sdp_dir,
                                                             stderr))
            raise CbaHelperException("Failed to create temp dir on node")
        self.runner = self._get_camp_runner(node_hostname, self.tmp_sdp_dir)
        for sdp_name, sdp_path in self.sdp_files.items():
            self.runner.transfer_sdp(os.path.dirname(sdp_path), sdp_name)
            self.runner.import_sdp(sdp_name)

    def _clean_up(self, node_hostname):
        rc, _, stderr = self._execute(node_hostname,
                                           "rm -rf %s" % self.tmp_sdp_dir)
        if rc != 0:
            log.trace.warning("Failed to remove tmp SDP dir %s: %s" % (
                                                            self.tmp_sdp_dir,
                                                                     stderr))
        # TODO remove campaign SDP

    def _execute_campaign(self, node_hostname):
        '''
        Method should be overridden
        '''
        self.runner.execute_campaign(self.campaign_name)
        self._clean_up(node_hostname)

    def _post_check(self):
        '''
        Method should be overridden
        '''
        pass

    #### Upgrade task ####
    def upgrade_sw(self, callback_api, node_name):
        pass

    #### Helper Methods ###
    def _execute(self, hostname, cmd):
        return execute(hostname, cmd)

    def _determine_primary_node(self, cluster):
        return [
           q.hostname for q in cluster.query("node") if q.node_id == '1'][0]

    def _get_camp_runner(self, node_hostname, camp_dir):
        return CampaignRunner(node_hostname, camp_dir)

    def _is_cmw_ready(self, node_hostname):
        #ensure cmw is installed
        cmd = "cmw-status node"
        retcode, stdout, _ = self._execute(node_hostname, cmd)
        if not retcode == 0 or not stdout == "Status OK":
            log.trace.error("CMW precheck failed")
            raise CMWStateError("CMW precheck failed")

    def _is_component_installed(self, node_hostname, comp_sdp):
        cmd = ("cmw-repository-list |grep %s |"
               "awk '{print $2}'") % comp_sdp
        rc, stdout, _ = self._execute(node_hostname, cmd)
        if rc != 0:
            log.trace.info("Failed executing command '{0}' on node '{1}'".\
                                                                format(cmd,
                                                                node_hostname))
        return stdout == "Used"
