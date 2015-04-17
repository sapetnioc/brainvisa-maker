import subprocess

from bv_build.workers import RequirementWorker

class AptWorker(RequirementWorker):
    @staticmethod
    def check_module_requirement(dir_manager, module, verbose, name):
        worker_cache = dir_manager.cache.setdefault('workers',{}).setdefault('apt',{})
        if not worker_cache.get(name):
            if verbose:
                print >> verbose, 'Checking apt-get package', name
            installed = True
            output = subprocess.check_output(['apt-cache', '-n', 'search', 
                                             '^%s$' % name])
            if not output:
                installed = False
            else:
                dpkg = output.split(None, 1)[0]
                if verbose:
                    print >> verbose, '=> Checking dpkg package', dpkg
                if subprocess.call(['dpkg', '-L', dpkg], 
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT):
                    installed = False
            if worker_cache.get(name) != installed:
                worker_cache[name] = installed
                dir_manager.save_cache()
            return installed
        else:
            if verbose:
                print >> verbose, 'Skip checking of apt-get package', name, \
                                  'marked as installed in cache'
        return True
    
    @staticmethod
    def missing_requirements_error_message(dir_manager, missing_requirements):
        missing = [r['name'] for r in missing_requirements]
        return ('Some required packages are not installed on '
                'the system. Please use the following command: '
                'sudo apt-get install %s' % \
                ' '.join(missing))
