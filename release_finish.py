from git import Repo
import os.path as osp
import shutil
import argparse
from constants import *


env = ''


def get_start_branch(repo):
    """
    Check for release branch, if found ask for confirm, else return develop
    :param repo:
    :return:
    """
    for branch in repo.remotes['origin'].refs:
        result = re.match('origin/release/(.*)', branch.name)
        if result:
            release_version = result.group(1)
            sys.stdout.write("Release branch found [%s], start from here? [Y/n]" % branch.name)
            choice = raw_input().lower()
            if choice == 'y' or choice == '':
                return release_version
            else:
                sys.stderr.write("Ok, as you wish, bye!!")
                sys.exit()
    sys.stderr.write("No release branch found!!")
    sys.exit()


def release_finish(project):
    """
    :param project:

    """

    execute_command(ADD_SSH_CERT_CMD)
    # execute_command(CHANGE_JAVA_HOME_COMMAND % JAVA_TARGET)

    project_path = get_project_path(project)

    gt = Repo.clone_from(PROJECT_GIT % project, project_path).git
    # check for a release branch

    repo = Repo(project_path)
    version = get_start_branch(repo)

    release_branch = 'release/%s' % version

    gt.checkout(release_branch)

    root_path = find_root_project(project_path)
    print "Root path :%s" % root_path
    os.chdir(root_path)

    execute_command(MAVEN_VERSION_SET_CMD % version)
    execute_command(MAVEN_VERSION_COMMIT_CMD)

    for item in repo.index.diff(None):
        print 'adding %s' % item.a_path
        pom_to_add = osp.join(project_path, item.a_path)
        repo.index.add([pom_to_add])

    print repo.git.status()
    repo.index.commit(GIT_COMMIT_COMMENT % version)

    #handle_opened_mr(project)
    # TODO do it in release_start, in the end
    #create_merge_request(release_branch, project)

    execute_command(MAVEN_RELEASE_FINISH_CMD % env)

    remote = repo.remote(name='origin')

    remote.push(all=True)
    remote.push(tags=True)
    remote.push(refspec=':%s' % release_branch)

    print "Done (I hopes)!!"
    shutil.rmtree(project_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Input parameters')
    parser.add_argument('repo_name', metavar='repository', type=str, help='Repository name')
    parser.add_argument('-j', '--jre', nargs='?', type=str, default='6', help='JRE version')
    parser.add_argument('-t', '--team', nargs='?', type=str, default='lcert', help='Development Team')

    args = parser.parse_args()

    print '%s ' % args.repo_name

    env = set_environment(args.jre)
    try:
        release_finish(args.repo_name)
    except Exception as err:
        print("error: {0}".format(err))
        shutil.rmtree(get_project_path(args.repo_name))
