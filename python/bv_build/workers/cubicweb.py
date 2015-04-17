import os
import os.path as osp
import subprocess
import re

from bv_build.workers import RequirementWorker
from bv_build.subprocess_utils import silent_or_exit_call

class CubicwebWorker(RequirementWorker):
    @staticmethod
    def check_module_requirement(dir_manager, module, verbose, name, version=None):
        worker_cache = dir_manager.cache.setdefault('workers',{}).setdefault('cubicweb',{})
        cached_version = worker_cache.get(name)
        if cached_version is None or (version is not None and cached_version != version):
            if verbose:
                print >> verbose, 'Checking Cubicweb cube', name
            cube_dir=osp.join(dir_manager.directory,'share','cubicweb','cubes', name)
            if not osp.exists(cube_dir):
                if verbose:
                    print >> verbose, 'Cube directory does not exist: %s' % cube_dir
                return False
            output = subprocess.check_output(['hg', '--cwd', cube_dir, 'summary'])
            found_version = None
            for i in output.split('\n'):
                if i.startswith('parent:'):
                    tag = i.split()[-1]
                    l = tag.split('-version-')
                    if len(l) == 2:
                        found_version = l[1]
                    break
            if verbose:
                print >> verbose, 'Cube %s has version %s' % (name, found_version)
            if found_version:
                worker_cache[name] = found_version
                dir_manager.save_cache()
            return found_version == version
        else:
            if verbose:
                print >> verbose, 'Skip checking of Cubicweb cube', name, \
                                  'marked as version %s in cache' % cached_version
        return True
        
    @staticmethod
    def cube_version(cube_dir):
        output = subprocess.check_output(['hg', '--cwd', cube_dir, 'tags'])
        cube = osp.basename(cube_dir)
        pattern = re.compile(r'cubicweb-%s-version-(\d+).(\d+).(\d+) .*' % cube)
        cube_versions = []
        for i in output.split('\n'):
            m = pattern.match(i)
            if m:
                cube_versions.append(tuple(int(i) for i in m.groups()))
        cube_versions.sort()
        return cube_versions
        
    @classmethod
    def resolve_requirement(cls, dir_manager, verbose, name, version=None):
        cubes_dir=osp.join(dir_manager.directory,'share','cubicweb','cubes')
        if not osp.exists(cubes_dir):
            os.makedirs(cubes_dir)
        print 'Downloading cube', name
        cube_dir = osp.join(cubes_dir,name)
        if not osp.exists(cube_dir):
            silent_or_exit_call(['hg', '--cwd', cubes_dir, 'clone', 'http://hg.logilab.org/cubes/%s' % name])
        if version:
            choosen_version = tuple(int(i) for i in version.split('.'))
        else:
            choosen_version = cls.cube_versions(cube_dir)[-1]
        silent_or_exit_call(['hg', '--cwd', cube_dir, 'update', 'cubicweb-%s-version-%d.%d.%d' % ((name,)+choosen_version)])

    @staticmethod
    def missing_requirements_error_message(dir_manager, missing_requirements):
        missing = [('%s=%s' % (r['name'], r['version']) if r['version'] else r['name']) for r in missing_requirements]
        return ('Some required Cubicweb cube do not have a required version: %s' % \
                ' '.join(missing))
