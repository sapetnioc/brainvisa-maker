import os.path as osp
import subprocess

from bv_build.workers import SourceWorker
from bv_build.subprocess_utils import verbose_check_call

class SvnWorker(SourceWorker):
    @staticmethod
    def source_status(dir_manager, module):
        src_dir = dir_manager.source_directory(module)
        if osp.exists(src_dir):
            output = subprocess.check_output(['svn', 'status', src_dir])
            return 'svn status %s\n%s' % (src_dir, output)
        else:
            return 'directory %s does not exist' % src_dir

    @staticmethod
    def source_update(dir_manager, module, verbose):
        src_dir = dir_manager.source_directory(module)
        source = dir_manager.repository.module_source(module)
        url = source['url']
        print 'Updating %s source with svn' % module
        if osp.exists(src_dir):
            cmd = ['svn', 'update', src_dir]
        else:
            cmd = ['svn', 'checkout', url, src_dir]
        verbose_check_call(cmd, verbose=verbose)
