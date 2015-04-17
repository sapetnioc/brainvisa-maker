import os.path as osp
import glob
import re

def parse_project_info_cmake( path ):
  """Parses a project_info.cmake file
  
  @type path: string
  @param path: The path of the project_info.cmake file
  
  @rtype: tuple
  @return: A tuple that contains project name, component name and version
  """
  project = None
  component = None
  version = {'major' : None,
             'minor' : None,
             'micro' : None}

  p = re.compile( r'\s*set\(\s*([^ \t]*)\s*(.*[^ \t])\s*\)' )
  for line in open( path ):
    match = p.match( line )
    if match:
      variable, value = match.groups()
      if variable == 'BRAINVISA_PACKAGE_NAME':
        component = value
      elif variable == 'BRAINVISA_PACKAGE_MAIN_PROJECT':
        project = value
      elif variable == 'BRAINVISA_PACKAGE_VERSION_MAJOR':
        version[ 'major' ] = value
      elif variable == 'BRAINVISA_PACKAGE_VERSION_MINOR':
        version[ 'minor' ] = value
      elif (variable == 'BRAINVISA_PACKAGE_VERSION_PATCH') :
        version[ 'micro' ] = value
        
  return ( project, component, version )

def parse_project_info_python( path ):
  """Parses an info.py file
  
  @type path: string
  @param path: The path of the info.py file
  
  @rtype: tuple
  @return: A tuple that contains project name, component name and version
  """

  d = {}
  version = {}
  execfile(path, d, d)
  for var in ('NAME', 'version_major', 'version_minor', 'version_micro'):
    if var not in d:
      raise KeyError('Variable %s missing in info file %s' % (var, path))
    
  project = component = d['NAME']
  version['major'] = d['version_major']
  version['minor'] = d['version_minor']
  version['micro'] = d['version_micro']
  
  return ( project, component, version )

def find_project_info(directory):
  """Find the project_info.cmake or the info.py file
     contained in a directory.
     Files are searched using the patterns :
     1) <directory>/project_info.cmake
     2) <directory>/python/*/info.py
     3) <directory>/*/info.py
     
  @type directory: string
  @param directory: The directory to search project_info.cmake or info.py
  
  @rtype: string
  @return: The path of the found file containing project information
           or None when no file was found
  """
  project_info_cmake_path = osp.join( directory,
                                          'project_info.cmake' )
  project_info_python_pattern = osp.join( directory,
                                              'python',
                                              '*',
                                              'info.py' )
  project_info_python_fallback_pattern = osp.join( directory,
                                                       '*',
                                                       'info.py' )

  # Searches for project_info.cmake and info.py file
  for pattern in ( project_info_cmake_path,
                    project_info_python_pattern,
                    project_info_python_fallback_pattern ):
    project_info_python_path = glob.glob( pattern )
  
    if project_info_python_path:
      return project_info_python_path[0]
  
  return None


def read_project_info(directory):
  """Find the project_info.cmake or the info.py file
     contained in a directory and parses its content.
     Files are searched using the patterns :
     1) <directory>/project_info.cmake
     2) <directory>/python/*/info.py
     3) <directory>/*/info.py
     
  @type directory: string
  @param directory: The directory to search project_info.cmake or info.py
  
  @type version_format: string
  @param version_format: The format to use to return version. Available 
                         keys in format string are major, minor and micro.
                         default: %(major)s.%(minor)s.%(micro)s
  
  @rtype: tuple
  @return: A tuple that contains project name, component name and version
  """
  project_info = None
  project_info_path = find_project_info( directory )
  
  if project_info_path is not None:
    
    if project_info_path.endswith( '.cmake' ):
      project_info = parse_project_info_cmake( project_info_path )
      
    elif project_info_path.endswith( '.py' ):
        project_info = parse_project_info_python( project_info_path )
        
    else:
      raise RuntimeError( 'File ' + project_info_path + ' has unknown '
                        + 'extension for project info file.'  )
      
    return project_info
