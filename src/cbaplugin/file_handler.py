##############################################################################
# COPYRIGHT Ericsson AB 2013
#
# The copyright to the computer program(s) herein is the property of
# Ericsson AB. The programs may be used and/or copied only with written
# permission from Ericsson AB. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

'''
Created on Jan 22, 2014

@author: terence.meyler
'''
import tarfile
import os
from litp.core.litp_logging import LitpLogger
import shutil
from cbaplugin.cba_exceptions import FileHandlerException

log = LitpLogger()


class FileHandler(object):
    '''
    Class FileHandler is responsible for reading the plugin config file,
    checking tar files exist, necessary sdp's are within the tarfile and
    extract those sdp's.
    '''

    def __init__(self, component, tar_directory, extract_directory):
        '''
        Constructor

        :param component: Name of component using this class
        :type component: string
        :param tar_directory: Location of the tar files to extract
        :type tar_directory: string
        :param extract_directory:  Location for the sdps
        :type extract_directory:   String
        '''

        if tar_directory is "":
            log.trace.exception(
                    "%s : Tar Directory location not specified" % component)
            raise FileHandlerException("No tar Directory specified for"
                                       " Filehandler Class")

        if extract_directory is "":
            log.trace.exception(
                    "%s :Extract Directory location not specified" % component)
            raise FileHandlerException("No Extract Directory specified for"
                                       " Filehandler Class")

        self.extract_directory = extract_directory
        self.tar_dir = tar_directory
        self.component = component

    def clean_sdp_install_dir(self):
        '''
        Removes the sdp directory on the ms
        '''
        shutil.rmtree(self.extract_directory)

    def untar_file(self, filename):
        '''
            Extract all files from a tar file.
            Raises an exception if it fails.

            :param filename: Tar file to be opened
            :type filename: string
        '''
        tar = None
        filename = os.path.join(self.tar_dir, filename)
        if not tarfile.is_tarfile(filename):
            log.trace.exception("%s : %s is not a tar file" %
                                    (self.component, filename))
            raise FileHandlerException("File is not a tar file")
        try:
            tar = tarfile.open(filename)
            tar.extractall(path=self.extract_directory)
        except Exception as error:
            log.trace.exception("%s :  %s" % (self.component, error))
            raise FileHandlerException("Filehandler encountered an error "
                                        "opening/extracting tar file")
        finally:
            if tar:
                tar.close()
