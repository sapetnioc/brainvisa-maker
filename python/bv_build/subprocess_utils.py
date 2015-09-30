import sys
import subprocess

def silent_check_call(command, cwd=None, env=None, exit=False):
    '''
    Call a command without printing any output but raises a
    subprocess.CalledProcessError containing the full command output (both
    stdout and stderr) if the return code of the command is not zero.
    '''
    p = subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,cwd=cwd, env=env)
    stdout = p.communicate()[0]
    if p.returncode:
        if exit:
            print >> sys.stderr,  'Command failed: %s\nCommand output:\n%s' % (' '.join('"%s"' % i for i in command), stdout)
            sys.exit(1)
        else:
            raise subprocess.CalledProcessError(p.returncode,command,stdout)

def silent_or_exit_call(*args,**kwargs):
    try:
        silent_check_call(*args, **kwargs)
    except subprocess.CalledProcessError, e:
        print >> sys.stderr,  'Command failed: %s\nCommand output:\n%s' % (' '.join('"%s"' % i for i in e.cmd), e.output)
        sys.exit(1)

def verbose_check_call(command, cwd=None, verbose=None):
    if verbose:
        subprocess.check_call(command, cwd=cwd, stdout=verbose, stderr=verbose)
    else:
        silent_check_call(command, cwd=cwd, exit=True)
