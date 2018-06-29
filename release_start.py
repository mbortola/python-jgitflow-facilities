from git import Repo
import os.path as osp
import shutil
import argparse
from constants import *
from secrets import PROJECT_GIT


env = ''


def get_start_branch(repo, version):
    """
    Check for release branch, if found ask for confirm, else return develop
    :param version:
    :param repo:
    :return:
    """
    for branch in repo.remotes['origin'].refs:
        result = re.match('origin/release/(.*)', branch.name)
        if result:
            release_version = result.group(1)
            if release_version != version:
                sys.stdout.write("Release branch found [%s], but different from input version, bye" % branch.name)
                sys.exit()
            sys.stdout.write("Release branch found [%s], start from here? [Y/n]" % branch.name)
            choice = raw_input().lower()
            if choice == 'y' or choice == '':
                return False, 'release/%s' % result.group(1)
            else:
                sys.stdout.write("ok, then do it by yourself.")
                sys.exit()
    return True, 'develop'


def find_next_rc(repo, version):

    max_rc = 0
    for tag in repo.tags:
        if tag.name.startswith(version):
            result = re.match('.*-RC(\d+)', tag.name)
            if not result:
                sys.stderr.write("You made some trouble with tag names, good luck")
                sys.exit()
            rc_found = int(result.group(1))
            if max_rc < rc_found:
                max_rc = rc_found
    if max_rc == 0:
        sys.stderr.write("No valid tag found for this version, what have you done??")
        sys.exit()
    next_rc = rc_found + 1
    sys.stdout.write('Create %s-RC%s? [Y/n]' % (version, next_rc))
    choice = raw_input().lower()
    if choice == 'y' or choice == '':
        return next_rc
    else:
        sys.stdout.write("ok, then do it by yourself.")
        sys.exit()


def release_start(version, project):
    """
    :param version:
    :param project:

    """

    project_path = get_project_path(project)

    gt = Repo.clone_from(PROJECT_GIT % project, project_path).git
    # check for a release branch

    repo = Repo(project_path)
    is_develop, branch_to_checkout = get_start_branch(repo, version)

    gt.checkout(branch_to_checkout)

    execute_command('ssh-add ~/.ssh/id_rsa')

    root_path = find_root_project(project_path)
    print "Root path :%s" % root_path
    os.chdir(root_path)

    if is_develop:
        # more stuff to do
        development_version = calculate_next_version(version)
        sys.stdout.write('Create release branch release/%s? [Y/n]' % version)
        choice = raw_input().lower()
        if choice != 'y' and choice != '':
            sys.stdout.write("ok, then do it by yourself.")
            sys.exit()
        execute_command(MAVEN_RELEASE_START_CMD % (env, version, development_version))
        rc_number = '1'
    else:
        # get the RC tag, add +1 and retag
        rc_number = find_next_rc(repo, version)

    # repo.git.custom_environment(GIT_SSH='/home/michele/mvn-jgitflow')

    tag_name = TAG_RC_NAME % (version, rc_number)

    execute_command(MAVEN_VERSION_SET_CMD % tag_name)
    execute_command(MAVEN_VERSION_COMMIT_CMD)

    for item in repo.index.diff(None):
        print 'adding %s' % item.a_path
        pom_to_add = osp.join(project_path, item.a_path)
        repo.index.add([pom_to_add])

    print repo.git.status()
    repo.index.commit(GIT_COMMIT_COMMENT % tag_name)

    release_branch = 'release/%s' % version

    repo.create_tag(ref=release_branch, path=tag_name)

    repo.remote(name='origin').push(tags=True)
    repo.remote(name='origin').push(all=True)

    # merge request from release to master
    if rc_number == '1':
        print "Creating merge request from release to master"
        create_merge_request(release_branch, project)

    print "Done (I hopes)!!"
    shutil.rmtree(project_path)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Input parameters')
    parser.add_argument('version', metavar='version', type=str,
                        help='The version to release (without SNAPSHOT or RC labels)')
    parser.add_argument('repo_name', metavar='repository', type=str, help='Repository name')
    parser.add_argument('-j', '--jre', nargs='?', type=str, default='6', help='JRE version')
    parser.add_argument('-t', '--team', nargs='?', type=str, default='lcert', help='Development Team')

    args = parser.parse_args()

    print '%s %s ' % (args.version, args.repo_name)

    env = set_environment(args.jre)
    try:
        release_start(args.version, args.repo_name)
    except Exception as err:
        print("error: {0}".format(err))
        shutil.rmtree(get_project_path(args.repo_name))
