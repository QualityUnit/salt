# -*- coding: utf-8 -*-
'''
Manage RabbitMQ Users
=====================

Example:

.. code-block:: yaml

    rabbit_user:
      rabbitmq_user.present:
        - password: password
        - force: True
        - tags:
          - monitoring
          - user
        - perms:
          - '/':
          - '.*'
          - '.*'
          - '.*'
        - runas: rabbitmq
'''

# Import python libs
from __future__ import absolute_import
import logging

# Import salt libs
import salt.utils
import salt.ext.six as six
from salt.exceptions import CommandExecutionError

log = logging.getLogger(__name__)


def __virtual__():
    '''
    Only load if RabbitMQ is installed.
    '''
    return salt.utils.which('rabbitmqctl') is not None


def _check_perms_changes(name, newperms, runas=None, existing=None):
    '''
    Check whether Rabbitmq user's permissions need to be changed.
    '''
    if not newperms:
        return False

    if existing is None:
        try:
            existing_perms = __salt__['rabbitmq.list_user_permissions'](name, runas=runas)
        except CommandExecutionError as err:
            log.error('Error: {0}'.format(err))
            return False

    perm_need_change = False
    for vhost_perms in newperms:
        for vhost, perms in vhost_perms.iteritems():
            if vhost in existing_perms:
                if perms != existing_perms[vhost]:
                    perm_need_change = True
            else:
                perm_need_change = True

    return perm_need_change


def _check_tags_changes(name, new_tags, runas=None):
    '''
    Whether Rabbitmq user's tags need to be changed
    '''
    if new_tags:
        if isinstance(new_tags, str):
            new_tags = new_tags.split()
        try:
            users = __salt__['rabbitmq.list_users'](runas=runas)[name] - set(new_tags)
        except CommandExecutionError as err:
            log.error('Error: {0}'.format(err))
            return []
        return users
    else:
        return []


def present(name,
            password=None,
            force=False,
            tags=None,
            perms=(),
            runas=None):
    '''
    Ensure the RabbitMQ user exists.

    name
        User name
    password
        User's password, if one needs to be set
    force
        If user exists, forcibly change the password
    tags
        Optional list of tags for the user
    perms
        A list of dicts with vhost keys and 3-tuple values
    runas
        Name of the user to run the command
    '''
    ret = {'name': name, 'result': False, 'comment': '', 'changes': {}}
    try:
        user = __salt__['rabbitmq.user_exists'](name, runas=runas)
    except CommandExecutionError as err:
        ret['comment'] = 'Error: {0}'.format(err)
        return ret

    if user and not any((force, perms, tags)):
        log.debug('RabbitMQ user \'{0}\' exists and force is not set.'.format(name))
        ret['comment'] = 'User \'{0}\' is already present.'.format(name)
        return ret

    if not user:
        if not __opts__['test']:
            log.debug('RabbitMQ user \'{0}\' doesn\'t exist - Creating.'.foramt(name))
            try:
                __salt__['rabbitmq.add_user'](name, password, runas=runas)
            except CommandExecutionError as err:
                ret['comment'] = 'Error: {0}'.format(err)
                return ret
        ret['changes'].update({'user':
                              {'old': '',
                               'new': name}})
    else:
        log.debug('RabbitMQ user \'{0}\' exists'.format(name))
        if force:
            if password is not None:
                if not __opts__['test']:
                    try:
                        __salt__['rabbitmq.change_password'](name, password, runas=runas)
                    except CommandExecutionError as err:
                        ret['comment'] = 'Error: {0}'.format(err)
                        return ret
                ret['changes'].update({'password':
                                      {'old': '',
                                       'new': 'Set password.'}})
            else:
                if not __opts__['test']:
                    log.debug('Password for {0} is not set - Clearing password.'.format(name))
                    try:
                        __salt__['rabbitmq.clear_password'](name, runas=runas)
                    except CommandExecutionError as err:
                        ret['comment'] = 'Error: {0}'.format(err)
                        return ret
                ret['changes'].update({'password':
                                      {'old': 'Removed password.',
                                       'new': ''}})

    new_tags = _check_tags_changes(name, tags, runas=runas)
    if new_tags:
        if not __opts__['test']:
            try:
                __salt__['rabbitmq.set_user_tags'](name, tags, runas=runas)
            except CommandExecutionError as err:
                ret['comment'] = 'Error: {0}'.format(err)
                return ret
        ret['changes'].update({'tags':
                              {'old': tags,
                               'new': new_tags}})
    try:
        existing_perms = __salt__['rabbitmq.list_user_permissions'](name, runas=runas)
    except CommandExecutionError as err:
        ret['comment'] = 'Error: {0}'.format(err)
        return ret

    if _check_perms_changes(name, perms, runas=runas, existing=existing_perms):
        for vhost_perm in perms:
            for vhost, perm in six.iteritems(vhost_perm):
                if not __opts__['test']:
                    try:
                        __salt__['rabbitmq.set_permissions'](
                            vhost, name, perm[0], perm[1], perm[2], runas=runas
                        )
                    except CommandExecutionError as err:
                        ret['comment'] = 'Error: {0}'.format(err)
                        return ret
                if ret['changes'].get('perms') is None:
                    ret['changes'].update({'perms':
                                          {'old': existing_perms,
                                           'new': ''}})
                ret['changes']['perms']['new'].update({vhost: perm})

    ret['result'] = True
    if ret['changes'] == {}:
        ret['comment'] = '\'{0}\' is already in the desired state.'.format(name)
        return ret

    if __opts__['test']:
        ret['result'] = None
        ret['comment'] = 'Configuration for \'{0}\' will change.'.format(name)
        return ret

    ret['comment'] = '\'{0}\' was configured.'.format(name)
    return ret


def absent(name,
           runas=None):
    '''
    Ensure the named user is absent

    name
        The name of the user to remove
    runas
        User to run the command
    '''
    ret = {'name': name, 'result': False, 'comment': '', 'changes': {}}

    try:
        user_exists = __salt__['rabbitmq.user_exists'](name, runas=runas)
    except CommandExecutionError as err:
        ret['comment'] = 'Error: {0}'.format(err)
        return ret

    if user_exists:
        if not __opts__['test']:
            try:
                __salt__['rabbitmq.delete_user'](name, runas=runas)
            except CommandExecutionError as err:
                ret['comment'] = 'Error: {0}'.format(err)
                return ret
        ret['changes'].update({'name':
                              {'old': name,
                               'new': ''}})
    else:
        ret['result'] = True
        ret['comment'] = 'The user \'{0}\' is not present.'.format(name)
        return ret

    if __opts__['test'] and ret['changes']:
        ret['result'] = None
        ret['comment'] = 'The user \'{0}\' will be removed.'.format(name)
        return ret

    ret['result'] = True
    ret['comment'] = 'The user \'{0}\' was removed.'.format(name)
    return ret
