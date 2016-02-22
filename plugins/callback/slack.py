import uuid
import json
import os
import socket
import requests

SLACK_INCOMING_WEBHOOK = 'https://hooks.slack.com/services/%s'
SLACK_TOKEN = os.getenv('SLACK_TOKEN')
SLACK_CHANNEL = os.getenv('SLACK_CHANNEL', '#ansible')
SLACK_USERNAME = os.getenv('SLACK_USERNAME', 'ansible')

def send_info(title, details=None, host=None):
    do_send(title, host, details, ':ghost:', 'good')

def send_error(title, host=None, details=None):
    do_send(title, host, details, ':japanese_goblin:', 'danger')

def pretty_print(data):
    return json.dumps(data, sort_keys=True, indent=4)

def do_send(title, host, details, icon, color):
    if SLACK_TOKEN is None or SLACK_TOKEN == '':
        return
    msg = [title]
    if host is not None:
        msg.append('\nhost: %s' % host)
    if details is not None:
        msg.append('\n%s' % details)
    msg = ' '.join(msg)
    payload = dict(attachments=[dict(
        fields=[dict(value=msg)],
        fallback=msg,
        color=color,
        author_icon=icon,
        mrkdwn_in=['text', 'fallback', 'fields'])])
    payload['icon_emoji'] = icon
    payload['color'] = color
    payload['channel'] = SLACK_CHANNEL
    payload['username'] = SLACK_USERNAME
    data = json.dumps(payload)
    webhook_url = SLACK_INCOMING_WEBHOOK % (SLACK_TOKEN)
    response = requests.post(webhook_url, data=data)
    if response.status_code not in (200, 201):
        print 'Could not submit message to Slack: {0}'.format(response.text)

class CallbackModule(object):
    def runner_on_failed(self, host, res, ignore_errors=False):
        send_error(
            title='Ansible failed',
            details=res)

    def runner_on_ok(self, host, res):
        pass

    def runner_on_error(self, host, msg):
        pass

    def runner_on_skipped(self, host, item=None):
        pass

    def runner_on_unreachable(self, host, res):
        send_error(title='Ansible host unreachable: %s' % host)

    def runner_on_no_hosts(self):
        pass

    def runner_on_async_poll(self, host, res, jid, clock):
        pass

    def runner_on_async_ok(self, host, res, jid):
        pass

    def runner_on_async_failed(self, host, res, jid):
        pass

    def playbook_on_start(self):
        send_info(
            title='Ansible playbook %s started on %s' % (self.playbook.filename, socket.gethostname()))

    def playbook_on_notify(self, host, handler):
        pass

    def playbook_on_no_hosts_matched(self):
        pass

    def playbook_on_no_hosts_remaining(self):
        pass

    def playbook_on_task_start(self, name, is_conditional):
        pass

    def playbook_on_vars_prompt(self, varname, private=True, prompt=None, encrypt=None, confirm=False, salt_size=None, salt=None, default=None):
        pass

    def playbook_on_setup(self):
        pass

    def playbook_on_import_for_host(self, host, imported_file):
        pass

    def playbook_on_not_import_for_host(self, host, missing_file):
        pass

    def playbook_on_play_start(self, pattern):
        pass

    def playbook_on_stats(self, stats):
        send_info(
            title="Ansible play complete",
            details="""total: {0}
ok: {1}
changed: {2}
unreachable: {3}
failed: {4}
skipped: {5}""".format(stats.processed, stats.ok, stats.changed, stats.dark, stats.failures, stats.skipped))
