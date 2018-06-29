__author__ = 'michele'

import requests
import json
from secrets import SLACK_TOKEN

base_url = 'https://slack.com/api/'

method_auth_test = 'auth.test'
method_channel_list = 'channels.list'
method_groups_list = 'groups.list'
method_im_list = 'im.list'
method_chat_delete = 'chat.delete'
method_chat_post = 'chat.postMessage'


def _token():
    return '?token=' + SLACK_TOKEN


def send_message(channel_id, message, username, as_user=False):

    parameters = {
        'token': SLACK_TOKEN,
        'channel': channel_id,
        'as_user': as_user,
        'username': username,
        'text': message
    }
    print json.dumps(parameters)
    response = requests.get(base_url + method_chat_post, params=parameters)
    return json.loads(response.content)


def get_base_info():
    response = requests.get(base_url + method_auth_test + '?token=' + SLACK_TOKEN)
    return json.loads(response.content)


def get_channel_list(exclude_archieved=False):
    if exclude_archieved:
        exclude_archieved_param = '&exclude_archieved=1'
    else:
        exclude_archieved_param = '&exclude_archieved=0'
    response = requests.get(base_url + method_channel_list + _token() + exclude_archieved_param)

    return json.loads(response.content).get('channels')


def get_groups_list(exclude_archieved=False):
    if exclude_archieved:
        exclude_archieved_param = '&exclude_archieved=1'
    else:
        exclude_archieved_param = '&exclude_archieved=0'
    response = requests.get(base_url + method_groups_list + _token() + exclude_archieved_param)

    return json.loads(response.content).get('groups')


def get_im_list():
    response = requests.get(base_url + method_im_list + _token())
    return json.loads(response.content).get('ims')


def delete_message(ts, channel):
    ts_argument = '&ts=' + ts
    channel_argument = '&channel=' + channel
    response = requests.get(base_url + method_chat_delete + _token() + ts_argument + channel_argument)


def _get_history(chat_type, channel, lastest=None, oldest=None, count=100, include_unreads=True):
    channel_arg = '&channel=' + channel
    lastest_arg = ('&lastest=' + lastest) if lastest else ''
    oldest_arg = ('&oldtest=' + oldest) if oldest else ''
    count_arg = '&count=' + str(count)
    include_unreads_arg = '&unreads=1' if include_unreads else ''

    response = requests.get(base_url + chat_type + '.history' + _token() + channel_arg + lastest_arg + oldest_arg +
                            count_arg + include_unreads_arg)

    response_dict = json.loads(response.content)
    return response_dict.get('messages'), response_dict.get('has_more')


def delete_all_channel_messages(channel_type, channel):
    delete_all = lambda x: delete_message(x.get('ts'), channel)

    messages, has_more = _get_history(channel_type, channel)

    map(delete_all, messages)
    while has_more:
        messages, has_more = _get_history(channel_type, channel)
        map(delete_all, messages)


def find_group_id_from_name(group_list, group_name):
    for group in group_list:
        if group.get('name') == group_name:
            return group.get('id')
    return None


if __name__ == "__main__":

    base_info = send_message('G720WLR7B', username='Libanese del bar', message='OK')

    print base_info
