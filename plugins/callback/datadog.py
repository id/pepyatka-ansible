from ConfigParser import ConfigParser
import imp
import json
import os
import uuid

from dogapi import dog_http_api as datadog

ROOT = os.path.dirname(__file__)

aggregation_key = uuid.uuid4().hex

parser = ConfigParser()
parser.read(os.path.join(ROOT, 'datadog.ini'))

def section(name):
    return dict(parser.items(name))

config = section('api')
datadog.api_key = config['api_key']
datadog.application_key = config['application_key']
if 'timeout' in config:
    datadog.timeout = int(config['timeout'])

events = section('events')
hooks = None
if 'hooks' in events:
    hooks_path = os.path.join(ROOT, events['hooks'])
    if os.path.isfile(hooks_path):
        with open(hooks_path) as f:
            hooks_name = os.path.basename(events['hooks'])
            parts = hooks_name.rpartition('.')
            module_name, suffix = (parts[0], '.'+parts[2]) if '.' in hooks_name else (module_name, '')
            hooks = imp.load_module(module_name, f, hooks_name, ('.py', 'r', imp.PY_SOURCE))

def event(title, tag, alert_type, text='', host=None):
    if hooks is None or hooks.enabled():
        tags = ['ansible:%s' % tag]
        if host is not None:
            if hasattr(hooks, 'get_host'):
                host = hooks.get_host(host)
            tags.append('host:%s' % host)
        datadog.event(
            title=title,
            text=text,
            tags=tags,
            alert_type=alert_type,
            aggregation_key=aggregation_key,
            source_type_name='ansible')

def pretty_print(data):
    return json.dumps(data, sort_keys=True, indent=4)

# TODO get priority, alert type via config/hooks
# TODO suppress events via config
# TODO events for rest of callbacks

class CallbackModule(object):
    def runner_on_failed(self, host, res, ignore_errors=False):
        # TODO don't swallow
        if not ignore_errors:
            event(
                title='Ansible task failed: %s' % res['invocation']['module_name'],
                text=pretty_print(res),
                host=host,
                alert_type='error',
                tag='failed')

    def runner_on_ok(self, host, res):
        changed = 'changed' if res.pop('changed', False) else 'ok'
        event(
            title='Ansible task %s: %s' % (changed, res['invocation']['module_name']),
            text=pretty_print(res),
            host=host,
            alert_type='info',
            tag=changed)

    def runner_on_error(self, host, msg):
        event(
            title='Ansible task errored',
            text=msg,
            host=host,
            alert_type='error',
            tag='errored')

    def runner_on_skipped(self, host, item=None):
        event(
            title='Ansible task skipped',
            text="Item: '%s'" % item,
            host=host,
            alert_type='info',
            tag='skipped')

    def runner_on_unreachable(self, host, res):
        event(
            title='Ansible task host unreachable: %s' % host,
            text=pretty_print(res),
            host=host,
            alert_type='error',
            tag='unreachable')

    def runner_on_no_hosts(self):
        pass

    def runner_on_async_poll(self, host, res, jid, clock):
        pass

    def runner_on_async_ok(self, host, res, jid):
        pass

    def runner_on_async_failed(self, host, res, jid):
        pass

    def playbook_on_start(self):
        event(
            title="Ansible playbook started",
            alert_type='info',
            tag='playbook_start')

    def playbook_on_notify(self, host, handler):
        pass

    def playbook_on_no_hosts_matched(self):
        pass

    def playbook_on_no_hosts_remaining(self):
        pass

    def playbook_on_task_start(self, name, is_conditional, skipped):
        if not skipped:
            event(
                title="Ansible task started%s: '%s'" % (' (conditional)' if is_conditional else '', name),
                alert_type='info',
                tag='task_start')

    def playbook_on_vars_prompt(self, varname, private=True, prompt=None, encrypt=None, confirm=False, salt_size=None, salt=None, default=None):
        pass

    def playbook_on_setup(self):
        pass

    def playbook_on_import_for_host(self, host, imported_file):
        pass

    def playbook_on_not_import_for_host(self, host, missing_file):
        pass

    def playbook_on_play_start(self, pattern):
        event(
            title="Ansible play started: '%s'" % pattern,
            alert_type='info',
            tag='play_start')

    def playbook_on_stats(self, stats):
        event(
            title="Ansible play complete",
            text="""total: {0}
ok: {1}
changed: {2}
unreachable: {3}
failed: {4}
skipped: {5}""".format(stats.processed, stats.ok, stats.changed, stats.dark, stats.failures, stats.skipped),
            alert_type='info',
            tag='play_complete')
