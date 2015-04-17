import os
import os.path as osp
import subprocess

from bv_build.workers import SourceWorker
from bv_build.subprocess_utils import verbose_check_call

class GitWorker(SourceWorker):
    @staticmethod
    def source_status(dir_manager, module):
        src_dir = dir_manager.source_directory(module)
        if osp.exists(src_dir):
            output = subprocess.check_output(['git', 'status'], cwd=src_dir)
            return 'git status in %s\n%s' % (src_dir, output)
        else:
            return 'directory %s does not exist' % src_dir

    @staticmethod
    def source_update(dir_manager, module, verbose):
        src_dir = dir_manager.source_directory(module)
        source = dir_manager.repository.module_source(module)
        url = source['url']
        remote_branch = source.get('branch', 'master')
        print 'Updating %s source with git' % module
        # Set a username in url if necessary
        git_user = getattr(dir_manager, 'git_user', None)
        if '@' not in url and git_user:
            url_head, url_tail = url.split('//', 1)
            url = '%s//%s@%s' % (url_head, git_user, url_tail)

        # Clone git repository if it does not exist yet locally
        if not osp.exists(osp.join(src_dir, '.git')):
            if osp.isdir(src_dir):
                if os.listdir(src_dir):
                    return ('directory "%s" is not empty, Git will not be able '
                        'to clone into it. This error may be due to a repository '
                        'change for a component (typically going from Subversion '
                        'to Git). You must check yourself that you have nothing '
                        'to keep in this directory and delete it to make '
                        '"bv_build update ..." work.') % src_dir
            else:
                os.makedirs(src_dir)
            if verbose:
                print >> verbose, ('directory %s is not a git repository => '
                    'clone from git %s') % (src_dir, url)
            verbose_check_call(['git', 'init', '--quiet'], cwd=src_dir,
                verbose=verbose)

        # Configure a remote for the developer's convenience
        retcode = subprocess.call(['git', 'remote', 'set-url', 'origin', url],
            stdout=open(os.devnull, 'w'), stderr=subprocess.STDOUT, 
            cwd=src_dir)
        if retcode != 0:
            subprocess.call(['git', 'remote', 'add', 'origin', url],
                            stdout=open(os.devnull, 'w'), stderr=subprocess.STDOUT,
                            cwd=src_dir)
            # Failure is ignored deliberately (the remote is just for convenience)

        # Get the SHA-1 identifiers of HEAD and refs/bv_head commits
        try:
            old_head = subprocess.check_output(
                ['git', 'rev-parse', '--quiet', '--verify', 'HEAD^{commit}'],
                cwd=src_dir)
        except subprocess.CalledProcessError:
            old_head = None
        try:
            old_bv_head = subprocess.check_output(
                ['git', 'rev-parse', '--quiet', '--verify',
                 'refs/bv_head^{commit}'],
                cwd=src_dir)
        except subprocess.CalledProcessError:
            old_bv_head = None

        # Fetch the remote branch specified in bv_build repository into 
        # refs/bv_head
        verbose_check_call(['git', 'fetch', url,
                               "+" + remote_branch + ":refs/bv_head"],
                              cwd=src_dir, verbose=verbose)

        # Check if we are in detached HEAD state
        retcode = subprocess.call(['git', 'symbolic-ref', '--quiet', 'HEAD'],
                                cwd=src_dir, stdout=open(os.devnull, 'w'),
                                stderr=subprocess.STDOUT)
        detached_head = False if retcode == 0 else True

        if (not old_head) or (detached_head and old_head == old_bv_head):
            # HEAD is detached, and is the same as left by the previous 
            # bv_build run: this is "follower mode", the remote ref can 
            # be checked out. This is safe to do even if there are local 
            # uncommitted changes, in which case "git checkout" will error
            # out appropriately.
            retcode = subprocess.call(['git', 'checkout', '--quiet',
                '--detach', 'refs/bv_head', '--'], cwd=src_dir)
            if retcode != 0:
                return '''\
The git repository at %s could not be updated,
please refer to the above error message.

If you have made local changes, you should keep track of them in a branch:
  git checkout -b <my_branch>
  git add ...
  git commit

Or, discard your changes and go back to following the upstream version:
  git checkout bv_head''' % src_dir
        elif not detached_head:
            # We are following a branch. Advance the branch if it has not 
            # diverged from upstream. If local commits exist, that would 
            # require creating a merge commit, and we do not want to do that 
            # behind the back of the developer. The (fetch + merge) command 
            # sequence is equivalent to "git pull --ff-only src remote_ref".
            # The merge aborts safely if there are local uncommitted changes,
            # and prints an appropriate message.
            retcode = subprocess.call(['git', 'merge', '--ff-only',
                'refs/bv_head'], cwd=src_dir)
            if retcode != 0:
                return '''\
Upstream changes could not be merged in %s,
please refer to the above message of "git merge".

If you do not want to develop in this repository anymore, you should
leave the branch and go back to tracking the upstream version:
  git checkout bv_head''' % src_dir
        else:
            # HEAD is detached but has been moved since last bv_maker run. The
            # user has likely checked out a tag manually, do not mess with
            # their repository.
            return '''\
The git repository at %s will not be updated by bv_maker,
because it is detached at a commit that does not correspond to bv_head.
If you did not do this on purpose, you should go back to following upstream:
  git checkout bv_head''' % src_dir
