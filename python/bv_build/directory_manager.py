import sys
import os.path as osp
from collections import OrderedDict
import subprocess
from cStringIO import StringIO

from .repository import Repository
from .yaml_utils import yaml_load, yaml_dump
from .subprocess_utils import silent_or_exit_call
from .workers import get_worker      

class DirectoryManager(object):
    default_repository_name = 'repository'
    cache_file = 'bv_build_cache.yml'
        
    @classmethod
    def cache_file_name(cls, directory):
        return osp.join(directory, cls.cache_file)
    
    @classmethod
    def create(cls, directory, repository=None, modules=None):
        directory = osp.normpath(osp.abspath(directory))
        cache_file = cls.cache_file_name(directory)
        if osp.exists(cache_file):
            raise RuntimeError('Cannot create directory, cache file already exists: %s' % cache_file)
        
        if repository is None:
            for path in (directory, osp.dirname(__file__)):
                repo_file = osp.join(path, cls.default_repository_name)
                if osp.exists(repo_file):
                    break
            else:
                raise RuntimeError('Cannot find repository file')
            repository = Repository(repo_file)
        elif isinstance(repository,Repository):
            repository = repository
        else:
            repository = Repository(repository)
        
        cache = OrderedDict(repository=repository.source, modules=modules)
        
        if modules is None:
            modules = repository.default_modules()
        if not modules:
            raise RuntimeError('Missing list of modules to use')
        
        if not osp.exists(osp.join(directory, 'bin', 'python')):
            silent_or_exit_call(['virtualenv', directory])
        yaml_dump(cache, open(cache_file,'w'))
    
    def __init__(self, directory):
        self.directory = osp.normpath(osp.abspath(directory))
        self.cache_file = self.cache_file_name(directory)
        self.cache = yaml_load(open(self.cache_file))
        self.repository = Repository(self.cache['repository'])
        self.modules = self.cache['modules']
        if self.modules is None:
            self.modules = self.repository.default_modules()

    def save_cache(self):
        yaml_dump(self.cache, open(self.cache_file,'w'))
    
    def clear_cache(self):
        self.cache = dict((i,self.cache[i]) for i in ('repository','modules'))
        self.save_cache()
            
    def status(self, out=sys.stdout):
        print >> out, 'Global information:'
        print >> out, '    Directory:', self.directory
        print >> out, '    Repository:', self.repository.source
        print >> out, '    Modules:', self.modules
        print >> out, '    Default modules:', not bool(self.cache['modules'])
        
        for module in self.repository.modules_dependencies(self.modules):
            module_cache = self.cache.get(module,{})
            print >> out
            print >> out, module + ':'
            has_missing = False
            missing_requirements = module_cache.get('missing requirements')
            if missing_requirements:
                print >> out, '    Missing requirements:'
                for requirement in missing_requirements:
                    req_yaml = yaml_dump(requirement, default_flow_style=False).strip().replace('\n','\n          ')
                    print >> out, '        - %s' % req_yaml
            elif missing_requirements is not None:
                    print >> out, '    Missing requirements: null'
            source = self.repository.module_source(module)
            if source is not None:
                src_yaml = yaml_dump(source, default_flow_style=False).strip().replace('\n','\n        ')
                print >> out, '    Source: '
                print >> out, '        %s' % src_yaml
                src_dir = self.source_directory(module)
                print >> out, '    Source directroy:', src_dir
                worker_name = source['type']
                worker = get_worker(worker_name, 'source')
                src_status = '\n        '.join(worker.source_status(self, module).split('\n'))
                print >> out, "    Source status: '\n        %s'" % src_status
        
        configure = self.cache.get('configure')
        if configure:
            print >> out, '    configure success:', str(configure['success']).lower()
            bv_maker = configure.get('bv_maker')
            if bv_maker:
                print >> out, '    bv_maker configure: |\n        %s' % bv_maker.replace('\n', '\n        ')

        build = self.cache.get('build')
        if build:
            print >> out, '    build success:', str(build['success']).lower()
            bv_maker = build.get('bv_maker')
            if bv_maker:
                print >> out, '    bv_maker build: |\n        %s' % bv_maker.replace('\n', '\n        ')

    def check_requirements(self, verbose=None):
        all_modules = list(self.repository.modules_dependencies(self.modules))
        for module in all_modules:
            module_cache = self.cache.get(module)
            if module_cache:
                module_cache.pop('missing requirements', None)
        used_workers = set()
        for module in all_modules:
            for requires in self.repository.module_requirements(module):
                r = requires.copy()
                worker_name = r.pop('type')
                worker = get_worker(worker_name, 'requirement')
                if worker not in used_workers:
                    worker.init_check_requirements(self, verbose)
                    used_workers.add(worker)
                if not worker.check_module_requirement(self, module, verbose, **r):
                    self.cache.setdefault(module,{}).setdefault('missing requirements',[]).append(requires)
            self.cache.setdefault(module,{}).setdefault('missing requirements', [])
            self.save_cache()
    
    def resolve_requirements(self, verbose=None):
        errors = []
        for module in self.repository.modules_dependencies(self.modules):
            module_cache = self.cache.get(module,{})
            missing_requirements = module_cache.get('missing requirements')
            if missing_requirements:
                for requirement in missing_requirements:
                    r = requirement.copy()
                    worker_name = r.pop('type')
                    worker = get_worker(worker_name, 'requirement')
                    error = worker.resolve_requirement(self, verbose, **r)
                    if error:
                        errors.append(error)
                    
        self.check_requirements(verbose=verbose)
        missing_by_worker_name = {}
        for module in self.repository.modules_dependencies(self.modules):
            module_cache = self.cache.get(module,{})
            missing_requirements = module_cache.get('missing requirements')
            if missing_requirements:
                for requirement in missing_requirements:
                    missing_by_worker_name.setdefault(requirement['type'], []).append(requirement)
        for worker_name, missing_requirements in missing_by_worker_name.iteritems():
            worker = get_worker(worker_name, 'requirement')
            errors.append(worker.missing_requirements_error_message(self,missing_requirements))
        return errors
    
    def source_directory(self, module):
        return osp.join(self.directory, 'src', module)
    
    def sources_update(self, verbose=None):
        for module in self.repository.modules_dependencies(self.modules):
            source = self.repository.module_source(module)
            if source is not None:
                worker_name = source['type']
                worker = get_worker(worker_name, 'source')
                error = worker.source_update(self, module, verbose=verbose)
                if error:
                    print >> sys.stderr, '\nERROR: %s' % error

    #def configure(self, verbose=None):
        #self.cache.pop('configure', None)
        #self.save_cache()
        #bv_maker_cfg = None
        #for module in self.repository.modules_dependencies(self.modules):
            #build = self.repository.module_build(module)
            #if build:
                #build_type = build['type']
                #if build_type == 'bv_maker':
                    #print 'Write bv_maker configuration for %s' % module
                    #if bv_maker_cfg is None:
                        #bv_maker_cfg = open(osp.join(self.directory, 'bv_maker.cfg'), 'w')
                        #print >> bv_maker_cfg, '[virtualenv $BV_MAKER_BUILD]'
                    #print >> bv_maker_cfg, '  directory $BV_MAKER_BUILD/src/%s' % module
                #else:
                    #print >> sys.stderr, 'ERROR: Unknown build type "%s" for module %s' % (build_type, module)
        #if bv_maker_cfg:
            #print 'Run bv_maker configure'
            #bv_maker_cfg.close()
            #if verbose:
                #cmd = ['bv_maker', '-v']
            #else:
                #cmd = ['bv_maker']
            #cmd += ['-b', self.directory, 'configure']
            
            #p = subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
            #sio = StringIO()
            #for line in p.stdout:
                #sio.write(line)
                #if verbose:
                    #sys.stdout.write(line)
                    #sys.stdout.flush()
            #p.poll()
            #self.cache  ['configure'] = { 
                #'success': (p.returncode == 0),
                #'bv_maker': sio.getvalue()}
            #self.save_cache()
            #if p.returncode is None:
                #print >> sys.stderr, 'ERROR: cannot get return code of bv_maker configure'
            #elif p.returncode:
                #print >> sys.stderr, 'ERROR: bv_maker configure failed'
    
    #def build(self, verbose=None):
        #if self.cache.get('configure',{}).get('success', False):
            #cmake_cache = osp.join(self.directory, 'CMakeCache.txt')
            #if not osp.exists(cmake_cache):
                #self.configure(verbose=verbose)
            #if osp.exists(cmake_cache):
                #print 'Run bv_maker build'
                #if verbose:
                    #cmd = ['bv_maker', '-v']
                #else:
                    #cmd = ['bv_maker']
                #cmd += ['-b', self.directory, 'build']
                
                #p = subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
                #sio = StringIO()
                #for line in p.stdout:
                    #sio.write(line)
                    #if verbose:
                        #sys.stdout.write(line)
                        #sys.stdout.flush()
                #p.poll()
                #self.cache  ['build'] = { 
                    #'success': (p.returncode == 0),
                    #'bv_maker': sio.getvalue()}
                #self.save_cache()
                #if p.returncode is None:
                    #print >> sys.stderr, 'ERROR: cannot get return code of bv_maker build'
                #elif p.returncode:
                    #print >> sys.stderr, 'ERROR: bv_maker build failed'
    
    def configure(self, verbose=None, release=True, debug=False):
        workers = {}
        for module in self.repository.modules_dependencies(self.modules):
            build = self.repository.module_build(module)
            if build:
                build = build.copy()
                build_type = build.pop('type')
                worker = workers.get(build_type)
                if worker is None:
                    worker = get_worker(build_type, 'build')
                    worker.start_configure(self, verbose, release=release, debug=debug)
                    workers[build_type] = worker
                worker.configure_module(self, verbose, module,**build)
        for worker in workers.itervalues():
            worker.terminate_configure(self, verbose)

    def build(self, verbose=None):
        workers = {}
        for module in self.repository.modules_dependencies(self.modules):
            build = self.repository.module_build(module)
            if build:
                build_type = build['type']
                worker = workers.get(build_type)
                if worker is None:
                    worker = get_worker(build_type, 'build')
                    worker.start_build(self, verbose)
                    workers[build_type] = worker
                worker.build_module(self, verbose, module)
        for worker in workers.itervalues():
            worker.terminate_build(self, verbose)
