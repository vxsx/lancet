import re

import keyring
from pygit2 import Repository
from jira.client import JIRA

from .harvest import HarvestPlatform
from .utils import cached_property


class MappedProjectID:
    def __init__(self, project_ids):
        self._project_ids = project_ids

    @classmethod
    def fromstring(cls, string):
        project_ids = string.split(',')
        project_ids = (p.split(':') for p in project_ids)
        project_ids = ((None, p) if len(p) == 1 else p for p in project_ids)
        project_ids = dict(project_ids)
        return cls(project_ids)

    def __call__(self, issue):
        try:
            return self._project_ids[str(issue.fields.issuetype)]
        except KeyError:
            pass

        try:
            return self._project_ids[None]
        except KeyError:
            pass

        raise ValueError('Could not find a project ID for issue type "{}"'
                         .format(issue.fields.issuetype))


class Lancet:
    def __init__(self, config):
        self.config = config

    @cached_property
    def repo(self):
        return Repository('./.git')

    def get_issue(self, key=None):
        # TODO: Move this method to the JIRA class

        if key is None:
            # TODO: This should be factored out of here
            match = re.search(r'feature/([A-Z]{2,}-[0-9]+)',
                              self.repo.head.name)
            if match is None:
                raise Exception('Unable to find current issue.')
            key = match.group(1)
        elif key.isdigit():
            project_key = self.config.get('tracker', 'default_project')
            if project_key:
                key = '{}-{}'.format(project_key, key)
        return self.tracker.issue(key)

    @cached_property
    def tracker(self):
        url = self.config.get('tracker', 'url')
        username = self.config.get('tracker', 'username')
        password = keyring.get_password('lancet+{}'.format(url), username)
        return JIRA(server=url, basic_auth=(username, password))

    @cached_property
    def timer(self):
        url = self.config.get('harvest', 'url')
        username = self.config.get('harvest', 'username')
        password = keyring.get_password('harvest+{}'.format(url), username)
        task_id = self.config.get('harvest', 'task_id')
        project_id_getter = MappedProjectID.fromstring(
            self.config.get('harvest', 'project_id'))
        return HarvestPlatform(server=url,
                               basic_auth=(username, password),
                               project_id_getter=project_id_getter,
                               task_id=task_id)