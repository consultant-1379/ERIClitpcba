'''
Created on Jan 28, 2014

@author: terence.meyler
'''

import unittest
from cbaplugin.file_handler import FileHandler
from cbaplugin.cba_exceptions import FileHandlerException
import mock


component = "Test Component"
tar_dir = "/tmp"
sdp_dir = "/tmp"


class TestFileHandler(unittest.TestCase):

    def setUp(self):
        self.fh = FileHandler(component, tar_dir, sdp_dir)

    @mock.patch('cbaplugin.file_handler.tarfile')
    def test_is_not_a_tarfile(self, tarfile):
        tarfile.is_tarfile.return_value = False
        try:
            self.fh.untar_file("file.txt")
        except FileHandlerException as e:
            self.assertEquals("File is not a tar file", str(e))
        else:
            self.fail("test_is_not_a_tarfile failed")

    @mock.patch('cbaplugin.file_handler.tarfile')
    def test_successfully_untar_a_file(self, tarfile):
        error = ""
        tarfile.is_tarfile.return_value = True
        tarfile.TarFile.extractall.return_value = True
        tarfile.TarFile.close().return_value = True
        self.fh.untar_file("file.tar")
        self.assertEqual(len(error), 0)

    @mock.patch('cbaplugin.file_handler.tarfile')
    def test_unsuccessfully_untar_a_file(self, tarfile):
        tarfile.is_tarfile.return_value = True
        tarfile.open.side_effect = Exception('Raise an exception')
        try:
            self.fh.untar_file("file.txt")
        except FileHandlerException as e:
            self.assertEquals("Filehandler encountered an error "
                                         "opening/extracting tar file", str(e))
        else:
            self.fail("Testcase: test_unsuccessfully_untar_a_file: FAILED")

    def test_tar_dir_not_specified(self):
        component = "Test Component"
        tar_dir = ""
        sdp_dir = "/tmp"
        try:
            self.fh = FileHandler(component, tar_dir, sdp_dir)
        except FileHandlerException as error:
            self.assertEquals("No tar Directory specified for Filehandler"
                                " Class", str(error))
        else:
            self.fail("Testcase: test_tar_dir_not_specified: Failed ")

    def test_sdp_dir_not_specified(self):
        component = "Test Component"
        tar_dir = "/tmp"
        sdp_dir = ""
        try:
            self.fh = FileHandler(component, tar_dir, sdp_dir)
        except FileHandlerException as error:
            self.assertEquals("No Extract Directory specified for Filehandler"
                                " Class", str(error))
        else:
            self.fail("Testcase: test_sdp_dir_not_specified: Failed ")


    def tearDown(self):
        pass
