'''
Created on 15-09-2011

@author: piotrhol
'''
import unittest
from sync.RosrsSync import RosrsSync
from sync.BackgroundSync import BackgroundResourceSync
from sync.test.TestConfig import ro_test_config
import logging
from os import rename
from os.path import exists

class Test(unittest.TestCase):
    
    files = { 'data/ro-test-1/subdir1/file1.txt',
             'data/ro-test-1/subdir1/file3.jpg',
             'data/ro-test-1/subdir1/subdir1-file.txt',
             'data/ro-test-1/subdir1/sub2dir/file2.txt' }
    fileToDelete = 'data/ro-test-1/subdir1/file1.txt'
    fileToReplace = 'data/ro-test-1/subdir1/file1beta.txt'

    def setUp(self):
        self.__sync = RosrsSync(ro_test_config.ROSRS_HOST, ro_test_config.ROSRS_USERNAME, ro_test_config.ROSRS_PASSWORD)
        self.__sync.postWorkspace()
        self.__sync.postRo(ro_test_config.RO_ID)
        self.__sync.postVersion(ro_test_config.RO_ID, ro_test_config.VER_ID)
        logging.basicConfig()
        logging.getLogger("sync.BackgroundSync").setLevel(logging.DEBUG)
        return

    def tearDown(self):
        self.__sync.deleteWorkspace()
        if (exists(self.fileToReplace)):
            rename(self.fileToReplace, self.fileToDelete)
        return

    def testSyncRecources(self):
        back = BackgroundResourceSync(self.__sync)
        
        (sent, deleted) = back.syncAllResources(ro_test_config.RO_ID, ro_test_config.VER_ID, \
                              "data/%s/%s" % (ro_test_config.RO_ID, ro_test_config.VER_ID))
        self.assertEquals(sent, self.files, "Sent files are not equal")
        assert len(deleted) == 0

        rename(self.fileToDelete, self.fileToReplace)
        (sent, deleted) = back.syncAllResources(ro_test_config.RO_ID, ro_test_config.VER_ID, \
                              "data/%s/%s" % (ro_test_config.RO_ID, ro_test_config.VER_ID))
        self.assertEquals(sent, {self.fileToReplace}, "New sent file")
        self.assertEquals(deleted, {self.fileToDelete}, "Deleted file")
        rename(self.fileToReplace, self.fileToDelete)
        return


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testSyncRecources']
    unittest.main()