from git import Repo
import shutil
import tempfile
import argparse
from constants import *

# clients usually are a java-6 affair..

env = ''


def release_client(version, project):
    """
    :param project: the project to release
    :param version: the version to release

    """

    # execute_command(CHANGE_JAVA_VERSION_COMMAND % 6)

    project_path = '%s/%s' % (tempfile.gettempdir(), project)

    gt = Repo.clone_from(PROJECT_GIT % project, project_path).git
    # check for a release branch

    repo = Repo(project_path)

    gt.checkout('develop')

    execute_command(ADD_SSH_CERT_CMD)

    root_path = find_root_project(project_path)
    print "Root path :%s" % root_path
    os.chdir(root_path)

    # more stuff to do
    development_version = calculate_next_version(version)
    sys.stdout.write('Create tag %s? [Y/n]' % version)
    if raw_input().lower() != 'y' and raw_input() != '':
        sys.stdout.write("ok, then do it by yourself.")
        sys.exit()
    execute_command(MAVEN_RELEASE_START_CMD % (env, version, development_version))

    create_merge_request('release/%s' % version, project)

    execute_command(MAVEN_RELEASE_FINISH_CMD % env)

    remote = repo.remote(name='origin')

    remote.push(all=True)
    remote.push(tags=True)
    # remote.push(refspec=':release/%s' % version)
    print "Done (I hopes)!!"
    shutil.rmtree(project_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Input parameters')
    parser.add_argument('version', metavar='version', type=str,
                        help='The version to release (without SNAPSHOT or RC labels)')
    parser.add_argument('repo_name', metavar='repository', type=str, help='Repository name')
    parser.add_argument('-j', '--jre', nargs='?', type=str, default='6', help='JRE version')

    args = parser.parse_args()

    print '%s %s ' % (args.version, args.repo_name)

    env = set_environment(args.jre)

    try:
        release_client(args.version, args.repo_name)
    except:
        shutil.rmtree(get_project_path(args.repo_name))
