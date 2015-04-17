from bv_build.workers import RequirementWorker

class ModuleWorker(RequirementWorker):    
    @staticmethod
    def check_module_requirement(dir_manager, module, verbose, **kwargs):
        return True
