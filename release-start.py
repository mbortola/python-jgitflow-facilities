import sys
from git import Repo
import os.path as osp
import gitlab
import shutil
import tempfile
import fnmatch
import re
import argparse
import os
import subprocess

# GITHUB_HOST = ' https://api.github.com'
GITLAB_HOST = 'http://gitlab.example.com'
# USER = 'michele'
# PASSWORD = 'infocert1'
# API_TOKEN = 'spA3JG_Ukzoowxd__c5b'

POM = 'pom.xml'

PROJECT_GIT = 'git@gitlab.example.com:psd/%s.git'
# CHECKOUT_ROOT = tempfile.gettempdir()
# PROJECT_PATH = CHECKOUT_ROOT + "%s"

MAVEN_RELEASE_START_CMD = 'mvn clean package jgitflow:release-start -DenableSshAgent=true -DreleaseVersion=%s' \
                          ' -DdevelopmentVersion=%s'
MAVEN_VERSION_SET_CMD = 'mvn versions:set -DnewVersion=%s'
MAVEN_VERSION_COMMIT_CMD = 'mvn versions:commit'

TAG_NAME = '%s-RC%s'
GIT_COMMIT_COMMENT = 'Release Candidate %s'


def calculate_next_version(release_version):
    regex_result = re.search('(\d).(\d).(\d)', release_version)
    last_number = 1 + int(regex_result.group(3))
    return '%s.%s.%s-SNAPSHOT' % (regex_result.group(1), regex_result.group(2), last_number)


def execute_command(command):
    process = subprocess.call([command], shell=True)
    print "{%s}: %s" % (command, process)
    if 0 != process:
        sys.stderr.write("Error on command execution, bye")
        sys.exit()


def find_root_project(project_path):
    def shortest_path(paths):
        return min(paths, key=lambda path: path.count('/'))

    matches = []
    for root, dirnames, filenames in os.walk(project_path):
        for filename in fnmatch.filter(filenames, POM):
            matches.append(root)
            print '%s - %s' % (root, filename)
    return shortest_path(matches)


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
            sys.stdout.write("Release branch found [%s], start from here? [y/n]" % branch.name)
            choice = raw_input().lower()
            if choice == 'y':
                return False, 'release/%s' % result.group(1)
            else:
                sys.stdout.write("ok, then do it by yourself.")
                sys.exit()
    return True, 'develop'


def find_next_rc(repo, version):

    max_rc = 1
    for tag in repo.tags:
        if tag.name.startswith(version):
            result = re.match('.*-RC(\d+)', tag.name)
            if not result:
                sys.stderr.write("You made some trouble with tag names, good luck")
                sys.exit()
            rc_found = int(result.group(1))
            if max_rc < rc_found:
                max_rc = rc_found
    next_rc = rc_found + 1
    sys.stdout.write('Create %s-RC%s? [y/n]' % (version, next_rc))
    choice = raw_input().lower()
    if choice == 'y':
        return next_rc
    else:
        sys.stdout.write("ok, then do it by yourself.")
        sys.exit()
    sys.stderr.write("No valid tag found for this version, what have you done??")
    sys.exit()


def release_start(version, project):
    """
    :param version:
    :param project:

    """

    project_path = '%s/%s' % (tempfile.gettempdir(), project)

    gt = Repo.clone_from(PROJECT_GIT % project, project_path).git
    # check for a release branch

    repo = Repo(project_path)
    is_develop, branch_to_checkout = get_start_branch(repo, version)

    gt.checkout(branch_to_checkout)

    root_path = find_root_project(project_path)
    print "Root path :%s" % root_path
    os.chdir(root_path)

    if is_develop:
        # more stuff to do
        development_version = calculate_next_version(version)
        sys.stdout.write('Create release branch release/%s? [y/n]' % version)
        if raw_input().lower() != 'y':
            sys.stdout.write("ok, then do it by yourself.")
            sys.exit()
        execute_command(MAVEN_RELEASE_START_CMD % (version, development_version))
        rc_number = '1'
    else:
        # get the RC tag, add +1 and retag
        rc_number = find_next_rc(repo, version)
    # ssh_cmd = 'ssh-add /home/michele/.ssh/id_rsa'
    # repo.git.custom_environment(GIT_SSH='/home/michele/mvn-jgitflow')

    tag_name = TAG_NAME % (version, rc_number)

    execute_command(MAVEN_VERSION_SET_CMD % tag_name)
    execute_command(MAVEN_VERSION_COMMIT_CMD)

    for item in repo.index.diff(None):
        print 'adding %s' % item.a_path
        pom_to_add = osp.join(project_path, item.a_path)
        repo.index.add([pom_to_add])

    print repo.git.status()
    repo.index.commit(GIT_COMMIT_COMMENT % tag_name)

    repo.create_tag(ref='release/%s' % version, path=tag_name)

    repo.remote(name='origin').push(all=True)
    repo.remote(name='origin').push(tags=True)
    print "Done (I hopes)!!"
    shutil.rmtree(project_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Input parameters')
    parser.add_argument('version', metavar='version', type=str,
                        help='The version to release (whitout SNAPSHOT or RC labels)')
    parser.add_argument('repo_name', metavar='repository', type=str, help='Repository name')

    args = parser.parse_args()

    print '%s %s ' % (args.version, args.repo_name)

    release_start(args.version, args.repo_name)

    pass
