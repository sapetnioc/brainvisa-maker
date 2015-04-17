class RequirementWorker(object):
    @staticmethod
    def init_check_requirements(dir_manager, verbose):
        pass
    
    @staticmethod
    def check_module_requirement(dir_manager, module, verbose, **kwargs):
        raise NotImplementedError()
    
    @staticmethod
    def resolve_requirement(dir_manager, verbose, **kwargs):
        raise NotImplementedError()
    
    @staticmethod
    def missing_requirements_error_message(dir_manager, missing_requirements):
        raise NotImplementedError()


class SourceWorker(object):
    pass

class BuildWorker(object):
    pass

worker_class_by_type = dict(
  requirement=RequirementWorker,
  source=SourceWorker,
  build=BuildWorker,
)

def get_worker(worker_name, worker_type):
    m = __import__('bv_build.workers.%s' % worker_name, fromlist=[''], level=0)
    worker_class = worker_class_by_type[worker_type]
    # Return one of the classes defined in module. There should be
    # exaclty one class.
    return (i for i in m.__dict__.itervalues() if isinstance(i,type) and 
        issubclass(i, worker_class) and i.__module__ == m.__name__).next()
