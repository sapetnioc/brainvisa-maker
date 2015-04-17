import sys
import os
import os.path as osp
import glob
from collections import OrderedDict

from bv_build.workers import BuildWorker
from bv_build.project_info import read_project_info
from bv_build.subprocess_utils import verbose_check_call


def create_site_customize(build_directory):
    # Create a sitecustomize Python package that imports all modules it
    # contains during Python startup. This is mainly used to modify sys.path
    # to include pure Python components source (see module 
    # brainvisa.maker.build_models.pure_python). This package is used only
    # in build directory, it is not installed in packages (to date there is
    # one exception to this in axon component, see Axon's CMakeLists.txt).
    sitecustomize_content = '''\
import os

for i in os.listdir(os.path.dirname(__file__)):
    if i.endswith('.py') and i != '__init__.py':
        module = i[:-3]
        __import__('sitecustomize.%s' % module)
'''
    sitecustomize_dir = osp.join(build_directory, 'python', 'sitecustomize')
    if not osp.exists(sitecustomize_dir):
        os.makedirs(sitecustomize_dir)
    open(osp.join(sitecustomize_dir,'__init__.py'), 'w').write(
        sitecustomize_content)

def cmake_path(path):
    '''
    Convert a system path to a CMakeLists.txt compatible path.
    '''
    if sys.platform == 'win32':
        return path.replace( '\\', '/' )
    else :
        return path

def cmake_command():
    if sys.platform == 'win32':
        return ['cmake', '-G', 'MSYS Makefiles']
    else:
        return ['cmake']

class BrainVISACMakeWorker(BuildWorker):

            
            
    @staticmethod
    def get_model(model_name):
        m = __import__('bv_build.workers.brainvisa_cmake_models.%s' % model_name, fromlist=[''], level=0)
        # Return one of the classes defined in module. There should be
        # exaclty one class.
        return (i for i in m.__dict__.itervalues() if isinstance(i,type) and 
            i.__module__ == m.__name__).next()
    
    @classmethod
    def start_configure(cls, dir_manager, verbose, release, debug):
        create_site_customize(dir_manager.directory)
        
        dir_manager.cache.setdefault('workers',{}).setdefault('brainvisa-cmake',{})['components'] = OrderedDict()
        
        # Save CMake build type in cache
        if release:
            build_type = ('RelWithDebInfo' if debug else 'Release')
        else:
            build_type = ('Debug' if debug else 'None')
        dir_manager.cache['workers']['brainvisa-cmake']['cmake_build_type'] = build_type
    
    @classmethod
    def configure_module(cls, dir_manager, verbose, module, model='genuine'):
        model = cls.get_model(model)
        model.configure_module(dir_manager, verbose, module)

    @classmethod
    def terminate_configure(cls, dir_manager, verbose):
        # Create bv_maker.cmake file
        sorted_components = dir_manager.cache['workers']['brainvisa-cmake']['components']
        cmakeFile = osp.join(dir_manager.directory, 'bv_maker.cmake')
        out = open( cmakeFile, 'w' )
        print >> out, 'set( BRAINVISA_PROJECTS build CACHE STRING "BrainVISA Projects list" FORCE )'
        print >> out, 'set( _BRAINVISA_PROJECTS build CACHE STRING "BrainVISA Projects list" FORCE )'
        print >> out, 'set( BRAINVISA_COMPONENTS', ' '.join(sorted_components),'CACHE STRING "BrainVISA components list" FORCE )'
        print >> out, 'set( _BRAINVISA_COMPONENTS', ' '.join(sorted_components),'CACHE STRING "BrainVISA components list" FORCE )'
        print >> out
        for component, component_cache in sorted_components.iteritems():
            print >> out, 'set( BRAINVISA_SOURCES_' + component + ' "' + cmake_path(component_cache['source_directory']) + '" CACHE STRING "Sources directory for component ' + component + '" FORCE )'
            print >> out, 'set( ' + component + '_DIR "' + cmake_path(component_cache['cmake_directory']) + '" CACHE STRING "Directory used for find_package( ' + component + ' )" FORCE )'
            print >> out, 'set( ' + component + '_VERSION "' + component_cache['version'] + '" )'
        out.close()

        cmakeLists = osp.join( dir_manager.directory, 'CMakeLists.txt' )
        out = open( cmakeLists, 'w' )
        print >> out, '''
cmake_minimum_required( VERSION 2.6 )
set( CMAKE_PREFIX_PATH "${CMAKE_BINARY_DIR}" ${CMAKE_PREFIX_PATH} )
find_package( brainvisa-cmake NO_POLICY_SCOPE )
include( "${brainvisa-cmake_DIR}/brainvisa-compilation.cmake" )
'''
        out.close()
        
        command = cmake_command()
        
        build_type = dir_manager.cache['workers']['brainvisa-cmake']['cmake_build_type']
        command += ['-DCMAKE_BUILD_TYPE:STRING=' + build_type, cmake_path(dir_manager.directory)]

        # set bv_maker path, so that cmake finds its modules
        os.environ['PATH'] = osp.join(dir_manager.directory, 'bin') + osp.sep \
            + os.getenv('PATH')
        verbose_check_call(command, cwd=dir_manager.directory, verbose=verbose)
  
  
    @classmethod
    def start_build(cls, dir_manager, verbose):
        pass
    
    @classmethod
    def build_module(cls, dir_manager, verbose, module, model='genuine'):
        model = cls.get_model(model)
        model.build_module(dir_manager, verbose, module)
    
    @classmethod
    def terminate_build(cls, dir_manager, verbose):
        # TODO manage make options
        command = ['make']
        verbose_check_call(command, cwd=dir_manager.directory, verbose=verbose)

  #def doc( self ):
    #self._process_configuration_lines()
    #system( cwd=self.directory, *( ['make'] + self.make_options.split() + ['-j1', 'doc'] ) )
  
  #def test( self ):
    #self._process_configuration_lines()
