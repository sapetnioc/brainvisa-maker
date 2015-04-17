import os
import os.path as osp

from bv_build.project_info import read_project_info

cmake_template = '''# This file was generated by bv_build
# Source file: %(file)s

cmake_minimum_required( VERSION 2.6 )

find_package( brainvisa-cmake REQUIRED )
SET( BRAINVISA_REAL_SOURCE_DIR "%(source_directory)s")
BRAINVISA_PROJECT()

BRAINVISA_DEPENDENCY( RUN DEPENDS python RUN ">= 2.5;<< 3.0" )
BRAINVISA_COPY_PYTHON_DIRECTORY( "%(source_directory)s/%(component_name)s"
                                 ${PROJECT_NAME} python/%(component_name)s
                                 INSTALL_ONLY )
find_package( python REQUIRED )
find_package( Sphinx )

BRAINVISA_GENERATE_SPHINX_DOC( "%(source_directory)s/doc/source"
    "share/doc/%(component_name)s-${BRAINVISA_PACKAGE_VERSION_MAJOR}.${BRAINVISA_PACKAGE_VERSION_MINOR}" )

set( BV_ENV_PYTHON_CMD 
     "${CMAKE_BINARY_DIR}/bin/bv_env" "${PYTHON_EXECUTABLE}" )

# tests
enable_testing()
add_test( %(component_name)s-tests "${CMAKE_BINARY_DIR}/bin/bv_env" "${PYTHON_EXECUTABLE}" "%(source_directory)s/test/test_%(component_name)s.py" )
UNSET( BRAINVISA_REAL_SOURCE_DIR)
'''

sitecustomize_module_content = '''# This file was generated by bv_build
# Source file: %s

import os.path as osp
import sys

path, ext = osp.splitext(__file__)
pth_file = path+'.pth'
main_dir = osp.dirname(osp.dirname(__file__))
try:
    i = sys.path.index(main_dir)
except ValueError:
    i = -1
sys.path[i:i] = open(pth_file).read().strip().split('\\n')
''' % __file__


class PurePythonModel(object):    
    @classmethod
    def configure_module(cls, dir_manager, verbose, module):
        # Create a bv_build_pure_python.py module in 
        # <build>/python/sitecustomize (which is created by bv_build). Modules
        # in this directory are loaded at Python startup time (only in the
        # buld tree, they are not installed in packages). This module adds the
        # content of bv_build_pure_python.pth file to sys.path, just before
        # the path <build>/python
        sitecustomize_dir = osp.join(dir_manager.directory, 'python', 'sitecustomize')
        if not osp.exists(sitecustomize_dir):
            os.makedirs(sitecustomize_dir)
        python_file = osp.join(sitecustomize_dir,'bv_build_pure_python.py')
        if not osp.exists(python_file) or open(python_file,'r').read() != sitecustomize_module_content:
            open(python_file,'w').write(sitecustomize_module_content)
            
        source_directory = osp.join(dir_manager.directory, 'src', module)
        project_info = read_project_info(source_directory)
        if project_info is None:
            raise RuntimeError('Cannot find project information (e.g. version) in %s' % source_directory)
        project, component, version = project_info
        full_version = '%(major)s.%(minor)s.%(micro)s' % version
        print 'Configure module', module, full_version

        # Make sure file in pth_path contains source_directory
        sitecustomize_dir = osp.join(dir_manager.directory, 'python', 'sitecustomize')
        pth_path = osp.join(sitecustomize_dir, 'bv_build_pure_python.pth')
        if osp.exists(pth_path):
            directories = open(pth_path).read().split()
        else:
            directories = []
        if source_directory not in directories:
            directories.append(source_directory)
            open(pth_path,'w').write('\n'.join(directories))
        
        # Create <build directory>/build_files/<component>_src/CMakeLists.txt
        src_directory = osp.join(dir_manager.directory, 'build_files', 
                                 '%s_src' % module)
        if not osp.exists(src_directory):
            os.makedirs(src_directory)
        cmakelists_content = cmake_template % dict(file=__file__,
            component_name=module,
            source_directory=src_directory)
        cmakelists_path = osp.join(src_directory, 'CMakeLists.txt')
        write_cmakelists = False
        if osp.exists(cmakelists_path):
            write_cmakelists = (open(cmakelists_path).read() != 
                                cmakelists_content)
        else:
            write_cmakelists = True
        if write_cmakelists:
            open(cmakelists_path,'w').write(cmakelists_content)

    @classmethod
    def build_module(cls, dir_manager, verbose, module):
        pass