import os
import os.path as osp

from bv_build.project_info import read_project_info
from bv_build.subprocess_utils import verbose_check_call
from bv_build.workers.brainvisa_cmake import cmake_command

class BrainVISACMakeGenuine(object):    
    @classmethod
    def configure_module(cls, dir_manager, verbose, module):
        source_directory = osp.join(dir_manager.directory, 'src', module)
        project_info = read_project_info(source_directory)
        if project_info is None:
            raise RuntimeError('Cannot find project information (e.g. version) in %s' % source_directory)
        project, component, version = project_info
        full_version = '%(major)s.%(minor)s.%(micro)s' % version
        print 'Configure module', module, full_version

        if module == 'brainvisa-cmake':
            build_dir = osp.join(dir_manager.directory, 'build_files', module)
            if not osp.exists(build_dir):
                os.makedirs(build_dir)
            command = cmake_command()
            command += ['-DCMAKE_INSTALL_PREFIX=%s' % dir_manager.directory, source_directory]
            verbose_check_call(command, cwd=build_dir, verbose=verbose)
            command = ['make', 'install']
            verbose_check_call(command, cwd=build_dir, verbose=verbose)
        else:
            short_version = '%(major)s.%(minor)s' % version
            cmake_directory = osp.join(dir_manager.directory, 'share', '%s-%s' % (module, short_version), 'cmake')
            components = dir_manager.cache['workers']['brainvisa-cmake']['components'][module] = {
                'source_directory': source_directory,
                'version': full_version,
                'cmake_directory': cmake_directory}

    @classmethod
    def build_module(cls, dir_manager, verbose, module):
        pass
