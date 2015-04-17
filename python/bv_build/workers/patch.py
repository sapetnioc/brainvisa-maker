import os.path as osp
import subprocess

from bv_build.workers import RequirementWorker
from bv_build.subprocess_utils import silent_check_call

class PatchWorker(RequirementWorker):
    @classmethod
    def check_module_requirement(cls, dir_manager, module, verbose, name):
        worker_cache = dir_manager.cache.setdefault('workers',{}).setdefault('patch',{})
        cached = worker_cache.get(name)
        if not cached:
            patch_file = cls.patch_file(dir_manager, name)
            if verbose:
                print >> verbose, 'Checking patch', name, '=', patch_file
            try:
                silent_check_call(['patch', '-p0', '--dry-run',
                    '--silent', '-N', '-i', patch_file ],
                    cwd=dir_manager.directory)
            except subprocess.CalledProcessError:
                if verbose:
                    print >> verbose, 'Patch cannot be applied'
                worker_cache[name] = True
                dir_manager.save_cache()
                return True
            if verbose:
                print >> verbose, 'Patch can be applied'
            return False
        else:
            if verbose:
                print >> verbose, 'Skip checking of patch', name, \
                                  'marked as applied in cache'
            return True
        
    @staticmethod
    def patch_file(dir_manager, name):
        return dir_manager.repository.get_file(name)
    
    @classmethod
    def resolve_requirement(cls, dir_manager, verbose, name):
        patch_file = cls.patch_file(dir_manager, name)
        print 'Applying patch', patch_file
        silent_or_exit_call(['patch', '-p0', '--silent', '-N', '-i', patch_file ],
            cwd=dir_manager.directory)
