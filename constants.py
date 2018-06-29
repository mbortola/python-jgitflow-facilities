
import sys
import subprocess
import fnmatch
import os
import re
import gitlab.v4
import gitlab
import tempfile
from secrets import GITLAB_HOST

MAVEN_RELEASE_START_CMD = '%s jgitflow:release-start -DenableSshAgent=true -DreleaseVersion=%s -DdevelopmentVersion=%s'
MAVEN_RELEASE_FINISH_CMD = '%s jgitflow:release-finish -DenableSshAgent=true'
MAVEN_VERSION_SET_CMD = 'mvn versions:set -DnewVersion=%s -DgenerateBackupPoms=false'
MAVEN_VERSION_COMMIT_CMD = 'mvn versions:commit'
ADD_SSH_CERT_CMD = 'ssh-add ~/.ssh/id_rsa'

POM = 'pom.xml'

TAG_NAME = '%s'
TAG_RC_NAME = '%s-RC%s'
GIT_COMMIT_COMMENT = 'Release Candidate %s'

API_TOKEN_ENV = "API_TOKEN"


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


def create_merge_request(release_branch, project):

    api_key = os.environ.get(API_TOKEN_ENV);

    gl = gitlab.Gitlab(GITLAB_HOST, api_key)
    gl.auth()

    project_id = gl.projects.get('lcert/%s' % project).id

    return gl.project_mergerequests.create({'source_branch': release_branch,
                                            'target_branch': 'master',
                                            'title': 'Release_finish',
                                            'description': 'Automatically opened Merge-request'},
                                           project_id=project_id)


def calculate_next_version(release_version):
    regex_result = re.search('(\d+).(\d+).(\d+)', release_version)
    last_number = 1 + int(regex_result.group(3))
    return '%s.%s.%s-SNAPSHOT' % (regex_result.group(1), regex_result.group(2), last_number)


def set_environment(jre):
    # sys.stdout.write("select Java environment? [6|7|8]: ")
    # choice = int(raw_input().lower())
    choice = int(jre)
    if 6 == choice:
        # environment = choice
        command = 'mvn3_0_5_jdk16'
    elif 7 == choice:
        command = 'mvn3_3_9_jdk17'
    elif 8 == choice:
        command = 'mvn' # default is mvn 3.3.9 and jdk 8
    else:
        sys.stdout.write("what?? No way")
        sys.exit()
    print "Setting environment for java %s" % choice
    # execute_command(JAVA_MAVEN_ENV_CMD % environment)
    return command


def get_project_path(project):
    return '%s/%s' % (tempfile.gettempdir(), project)


def handle_opened_mr(project):
    api_key = os.environ.get(API_TOKEN_ENV)

    gl = gitlab.Gitlab(GITLAB_HOST, api_key)
    gl.auth()

    project_id = gl.projects.get('lcert/%s' % project).id

    list = gl.project_mergerequests.list(project_id=project_id, state='opened')

    if len(list) == 1:
        print "You have an opened Merge request, force closing [y/N]? "
        choice = raw_input().lower()
        if choice != 'y':
            sys.stdout.write("ok, then do your stuff.")
            sys.exit()
        print "Ok, i will close it"
        list[0].state_event = 'close'
        list[0].save()
    elif len(list) > 1:
        print "You have too much opened merge request, Bye! "
        sys.exit()
    else:
        print "No opened Merge request found"
