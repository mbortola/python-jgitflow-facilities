import gitlab.v4
import gitlab
import slack_notifier
from secrets import *

string_list = []


def scan_project(project):

    try:
        mrs = project.mergerequests.list()
    except gitlab.exceptions.GitlabListError as err:
        print("error: {0}".format(err))
        return

    for mr in mrs:
        if mr.state == 'opened' and mr.merge_status == 'can_be_merged' and mr.target_branch == 'develop':
            approvals = mr.approvals.get()
            you_have_approved = False
            for approver in approvals.approved_by:
                if approver.get('user').get('id') == YOUR_USER_ID:
                    you_have_approved = True
            if approvals.approvals_left > 0:
                message = "Merge request: %s Approvals left %s" % (mr.web_url, approvals.approvals_left)
                if you_have_approved:
                    message + ' (And you are one of them)'
                string_list.append(message + '\n')
                print message


def get_opened_merge_requests():

    current_page = 1
    per_page = 20

    gl = gitlab.Gitlab(GITLAB_HOST, API_TOKEN)
    gl.auth()

    project_list = gl.projects.list(page=current_page, per_page=per_page)

    while len(project_list) > 0:
        current_page = current_page + 1
        project_list = gl.projects.list(page=current_page, per_page=per_page)
        print 'Readed %s projects at page %s' % (len(project_list), current_page)
        for prj in project_list:
            scan_project(prj)


if __name__ == "__main__":

    get_opened_merge_requests()
    print 'Scan Finished!'
    message = ''.join(string_list)
    print message
    # slack_notifier.send_message(SLACK_CR_CHANNEL, message=message, username='BOT')
