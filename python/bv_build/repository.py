import os.path as osp

import jinja2

from bv_build.yaml_utils import yaml_load

class Repository(object):
    def __init__(self, source):
        self.source = osp.normpath(osp.abspath(source))
    
    def get_distribution(self, distro_source):
        return Components(self, osp.join(self.source, distro_source))
    
    
def Distribution(object):    
    def __init__(self, source, repository=None):
        self.source = osp.normpath(osp.abspath(source))
        if repository is None:
            directory = osp.dirname(self.source)
            if not osp.exists(osp.join(directory), 'repository.yaml'):
                directory = osp.dirname(directory)
            repository = Repository(directory)
        self.repository = repository
        jinja2_string = open(self.source).read()
        env = jinja2.Environment(loader=jinja2.FileSystemLoader(self.repository.source))
        yaml_string = env.from_string(jinja2_string).render()
        self.distro = yaml_load(yaml_string)
    
    def get_file(self, file_name):
        return osp.join(self.repository.source, file_name)
    
    def default_modules(self):
        return self.distro['global information'].get('default modules', None)
    
    def module_dependencies(self, module):
        '''
        Parse the dependencies of a module to return an ordered list
        of dependent modules.
        '''
        done = set()
        for r in self.distro[module].get('requires',[]):
            if r['type'] == 'module' and r['name'] not in done:
                m = r['name']
                done.add(m)
                for dm in self.module_dependencies(m):
                    if dm not in done:
                        done.add(dm)
                        yield dm
                yield m
        if module not in done:
            yield module
                        
    def modules_dependencies(self, modules):
        '''
        Parse the dependencies of given modules to return an ordered list
        of dependent modules.
        '''
        done = set()
        for module in modules:
            for m in self.module_dependencies(module):
                if m not in done:
                    done.add(m)
                    yield m

    def module_requirements(self, module):
        return self.distro[module].get('requires',[])

    def module_source(self, module):
        return self.distro[module].get('source')
    
    def module_build(self, module):
        return self.distro[module].get('build')
