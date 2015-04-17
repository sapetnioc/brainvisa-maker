import os.path as osp

from bv_build.yaml_utils import yaml_load

class Repository(object):
    default_repository_file = 'bv_repos.yml'
    
    def __init__(self, source):
        self.source = osp.normpath(osp.abspath(source))
        self.repo = yaml_load(open(osp.join(self.source,'repository.yml')))
    
    def get_file(self, file_name):
        return osp.join(self.source, file_name)
    
    def default_modules(self):
        return self.repo['global information'].get('default modules', None)
    
    def module_dependencies(self, module):
        '''
        Parse the dependencies of a module to return an ordered list
        of dependent modules.
        '''
        done = set()
        for r in self.repo[module].get('requires',[]):
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
        return self.repo[module].get('requires',[])

    def module_source(self, module):
        return self.repo[module].get('source')
    
    def module_build(self, module):
        return self.repo[module].get('build')
