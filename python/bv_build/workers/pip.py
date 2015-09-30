import os
import os.path as osp
import subprocess

from bv_build.workers import RequirementWorker
from bv_build.subprocess_utils import silent_check_call

class PipWorker(RequirementWorker):
    @staticmethod
    def set_pip_command(dir_manager):
        if 'BRAINVISA_UNENV_PATH' in os.environ:
            dir_manager.pip_command = ['bv_unenv', osp.join(dir_manager.directory, 'bin', 'pip')]
        else:
            dir_manager.pip_command = [osp.join(dir_manager.directory, 'bin', 'pip')]
        
    @staticmethod
    def init_check_requirements(dir_manager, verbose):
        PipWorker.set_pip_command(dir_manager)
        pip_installed = {}
        for i in subprocess.check_output(dir_manager.pip_command + ['freeze']).split('\n'):
            if i:
                module, version = i.split('==')
                pip_installed[module] = version
        dir_manager.cache.setdefault('workers',{}).setdefault('pip',{})['installed'] = pip_installed    
        dir_manager.save_cache()
    
    @staticmethod
    def check_module_requirement(dir_manager, module, verbose, name, version=None):
        installed = dir_manager.cache['workers']['pip']['installed']
        installed_version = installed.get(name)
        if installed_version is None:
            if verbose:
                print >> verbose, 'pip: %s is not installed' % name
            return False
        if version is not None and installed_version != version:
            if verbose:
                print >> verbose, 'pip: %s installed version is %s but %s is expected' % (name, repr(installed_version), repr(version))
            return False
        if verbose:
            print >> verbose, 'pip: %s version %s is installed' % (name, version or installed_version)
        return True

    @staticmethod
    def resolve_requirement(dir_manager, verbose, name, version=None):
        if version:
            module = '%s==%s' % (name, version)
        else:
            module = name
        print 'pip install', module
        try:
            silent_check_call(dir_manager.pip_command + ['install', module])
        except subprocess.CalledProcessError, e:
            return 'Command failed: %s\nCommand output:\n%s' % (' '.join('"%s"' % i for i in e.cmd), e.output)
            
    @staticmethod
    def missing_requirements_error_message(dir_manager, missing_requirements):
        missing = [('%s==%s' % (r['name'], r['version']) if r.get('version') else r['name']) for r in missing_requirements]
        return ('Some required Python modules do not have a required version. '
                'Try using the following command: '
                '%s install %s' % \
                (' '.join(dir_manager.pip_command), ' '.join(missing)))
