#!/usr/bin/python

# Copyright: (c) 2024, Curtis Jones <cjones2@brocku.ca>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function

__metaclass__ = type


class ModuleDocFragment(object):
    DOCUMENTATION = r"""
---
attributes:
    check_mode:
        support: none
        description: Can not run in C(check_mode) and will not return changed status prediction without modifying target.
    diff_mode:
        support: none
        description: Will return details on what has changed (or possibly needs changing in C(check_mode)), when in diff mode.

options:
    api_key:
        description: DYNU Api Key (not oauth credentials)
        required: true
        type: str
    zone:
        description: DNS name of the zone to create the record under.
        required: true
        type: str
    node_name:
        description: Name of the DNS node.
        required: true
        type: str
    time_to_live:
        description: Time in seconds for record to be kept in DNS caches.
        required: false
        default: 60
        type: int
    group:
        description: Metadata tag to reference rules as a collective.
        required: false
        type: str
    state:
        description: Desired state of the expressed record.
        required: false
        default: 'present'
        type: str
        choices:
            - 'present'
            - 'absent'

author:
    - Curtis Jones (@brocktech)
"""
