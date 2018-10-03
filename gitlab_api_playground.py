import gitlab.v4
import gitlab
import slack_notifier
from secrets import *
from datetime import datetime
from datetime import timedelta
import json

merge_requests = []
approvers_stats = {}

DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%f'
APPROVED_MR_TEXT = 'approved this merge request'
NOW = datetime.now()
TWO_WEEKS_AGO = NOW - timedelta(days=7)


def scan_project(project):

    try:
        mrs = project.mergerequests.list()
    except gitlab.exceptions.GitlabListError as err:
        print("error: {0}".format(err))
        return

    for mr in mrs:
        days_passed = (NOW - datetime.strptime(mr.created_at[:-6], DATETIME_FORMAT)).days

        if valid_merge_request(mr):
            approvals = mr.approvals.get()
            discussions = mr.discussions.list()
            for discussion in discussions:
                notes = discussion.attributes['notes']
                for note in notes:
                    note_created_at_days = (NOW - datetime.strptime(note['created_at'][:-6], DATETIME_FORMAT)).days
                    if note['body'] == APPROVED_MR_TEXT and 14 > note_created_at_days:
                        user = note['author']['name']
                        fill_approvals_statistics(mr, user)

            if mr.state == 'opened':
                you_have_approved = False
                merge_request = {}
                for approver in approvals.approved_by:
                    if approver.get('user').get('id') == YOUR_USER_ID:
                        you_have_approved = True
                if approvals.approvals_left > 0:

                    merge_request['url'] = mr.web_url
                    merge_request['approvals_left'] = approvals.approvals_left
                    merge_request['approved_by_you'] = you_have_approved
                    merge_request['days'] = days_passed

                    if 'master' == mr.target_branch:
                        print 'skipped mr to master'
                    else:
                        merge_requests.append(merge_request)


def fill_approvals_statistics(merge_request, user):

    if user in approvers_stats:
        approvers_stats[user]['approvals'].append(merge_request.web_url)
    else:
        item = {'approvals': []}
        item.get('approvals').append(merge_request.web_url)
        approvers_stats[user] = item


def valid_merge_request(merge_request):

    # days_passed = (NOW - datetime.strptime(merge_request.created_at, DATETIME_FORMAT)).days
    upd_days_passed = (NOW - datetime.strptime(merge_request.updated_at[:-6], DATETIME_FORMAT)).days
    if upd_days_passed > 14 and merge_request.state != 'opened':
        # invalid mr
        return False
    return True


def print_result():
    sorted_list = sorted(merge_requests, key=lambda k: k['days'], reverse=True)
    string_list = []
    for item in sorted_list:
        string_list.append("Merge request: %s Approvals left %s Opened %s days ago.\n" %
                           (item['url'], item.get('approvals_left'), item['days']))

    print ''.join(string_list)
    print json.dumps(approvers_stats)


def get_opened_merge_requests():

    current_page = 1
    per_page = 30

    gl = gitlab.Gitlab(GITLAB_HOST, API_TOKEN)
    gl.auth()

    iterate = True

    while iterate:
        project_list = gl.projects.list(page=current_page, per_page=per_page)
        print 'Readed %s projects at page %s' % (len(project_list), current_page)
        for prj in project_list:
            scan_project(prj)
        if len(project_list) < per_page:
            iterate = False
        current_page = current_page + 1


if __name__ == "__main__":

    get_opened_merge_requests()
    print 'Scan Finished!'
    print_result()
    # slack_notifier.send_message(SLACK_CR_CHANNEL, message=message, username='BOT')
