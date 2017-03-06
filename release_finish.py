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
API_TOKEN = 'spA3JG_Ukzoowxd__c5b'

POM = 'pom.xml'

PROJECT_GIT = 'git@gitlab.example.com:psd/%s.git'
# CHECKOUT_ROOT = tempfile.gettempdir()
# PROJECT_PATH = CHECKOUT_ROOT + "%s"

MAVEN_RELEASE_FINISH_CMD = 'mvn clean package jgitflow:release-finish -DenableSshAgent=true'
MAVEN_VERSION_SET_CMD = 'mvn versions:set -DnewVersion=%s-SNAPSHOT'
MAVEN_VERSION_COMMIT_CMD = 'mvn versions:commit'

TAG_NAME = '%s-RC%s'
GIT_COMMIT_COMMENT = "update poms with SNAPSHOT version for jgitflow plugin"

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
            sys.stdout.write("Release branch found [%s], start from here? [y/n]" % branch.name)
            choice = raw_input().lower()
            if choice == 'y':
                return release_version
            else:
                sys.stderr.write("Ok, as you wish, bye!!")
                sys.exit()
    sys.stderr.write("Npo release branch found!!")
    sys.exit()


def create_merge_request(release_branch, project):

    gl = gitlab.Gitlab(GITLAB_HOST, API_TOKEN)
    gl.auth()

    project_id = gl.projects.get('psd/%s' % project).id

    gl.project_mergerequests.create({'source_branch': release_branch,
                                     'target_branch': 'master',
                                     'title': 'Release_finish'},
                                    project_id=project_id)


def release_finish(project):
    """
    :param project:

    """

    project_path = '%s/%s' % (tempfile.gettempdir(), project)

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
    repo.index.commit(GIT_COMMIT_COMMENT)

    create_merge_request(release_branch, project)

    execute_command(MAVEN_RELEASE_FINISH_CMD)

    repo.remote(name='origin').push(all=True)
    repo.remote(name='origin').push(tags=True)

    # remove release branch
    print "Done (I hopes)!!"
    shutil.rmtree(project_path)


# posizionandosi nel branch di release:
#    mvn versions:set -DnewVersion=x.y.z-SNAPSHOT```
#    mvn versions:commit
#    git commit -a -m "update poms with SNAPSHOT version for jgitflow plugin"
#    Creare una merge request, impostare come branch sorgente quello di release e branch destinazione il master
#        Associare la merge request alla milestone ```x.y.z```.
#    mvn jgitflow:release-finish
#    git push --all
#   git push --tags
#   git push origin :<branchName>

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Input parameters')
    parser.add_argument('repo_name', metavar='repository', type=str, help='Repository name')

    args = parser.parse_args()

    print '%s ' % args.repo_name

    release_finish(args.repo_name)
    pass
