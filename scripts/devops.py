# ejemplo:
# https://github.com/pallets/flask/blob/master/scripts/make-release.py
from subprocess import PIPE, Popen
import sys
import os
from slackclient import SlackClient

version = {}

version_filename = './credisur/version.py'

def main(args):
    old_version, new_version = bump_version()

    commands = [
        (add_all_to_git,),
        (commit_to_git, new_version),
        (push_to_remote_git,),
        (tag_commit, new_version),
        (push_tag_to_remote_git, new_version),
        (compile_sdist,),
        (compile_bdist,),
        (twine_upload,)
    ]

    all_succeded = run_all(commands)


    if not all_succeded:
        update_version_file(old_version)
        print("Execution failed. There were errors in the execution of commands.")
        return

    send_message_to_slack(new_version)


def send_message_to_slack(version):
    slack_token = os.environ["SLACK_API_TOKEN"]
    sc = SlackClient(slack_token)

    message = "Credisuretl se actualizó a la versión %s. El comando para actualizar es: `pip install --no-cache-dir --upgrade credisuretl`" % version

    sc.api_call(
        "chat.postMessage",
        channel="C5L54CYRK",
        text=message
    )

    print("message sent")


def update_version_file(version):
    with open(version_filename, 'w') as f:
        f.write("__version__= '%s'" % version)

def bump_version():
    exec(open(version_filename).read(), version)
    old_version = version['__version__']
    old_version_info = list(int(i) for i in old_version.split("."))
    new_version_info = [*old_version_info[:-1], old_version_info[-1] + 1]
    new_version = ".".join(str(i) for i in new_version_info)

    update_version_file(new_version)

    return (old_version, new_version)


def add_all_to_git():
    command = prepare_command(['git', 'add', '-A'])
    return run_command(command)

def commit_to_git(version):
    command = prepare_command(['git', 'commit', '-m', "'Release of version %s'" % version])
    return run_command(command)

def push_to_remote_git():
    command = prepare_command(['git', 'push'])
    return run_command(command)

def tag_commit(version):
    command = prepare_command(['git', 'tag', version])
    return run_command(command)

def push_tag_to_remote_git(version):
    #  git push origin <tag_name>
    command = prepare_command(['git', 'push', 'origin', version])
    return run_command(command)


def compile_sdist():
    command_args = 'python setup.py sdist'.split(" ")
    command = prepare_command(command_args)
    return run_command(command)

def compile_bdist():
    command_args = 'python setup.py bdist_wheel'.split(" ")
    command = prepare_command(command_args)
    return run_command(command)

def twine_upload():
    command_args = 'twine upload dist/*'.split(" ")
    command = prepare_command(command_args)
    return run_command(command)


def get_git_tags():
    return set(
        Popen(['git', 'tag'], stdout=PIPE).communicate()[0].splitlines()
    )

def prepare_command(command_args):

    return Popen(command_args, stdout=PIPE)

def run_command(process):
    stdout, stderr = process.communicate()

    if stderr:
        return False

    if stdout:
        print(stdout)

    return True

def run_all(commands):
    return all(x[0](*x[1:]) for x in commands)

def test_any():
    def try_x(x):
        print(x)
        return x == False

    any(try_x(x) for x in [1,2,False, 3,4,5])


if __name__ == '__main__':
    main(sys.argv[1:])
