#!/usr/bin/env python3
"""Fail before downloading/using AIR unless the owner has confirmed eligibility."""
import os
import sys


def check(environment):
    tier = environment.get('FLUMP_AIR_LICENSE_TIER', '')
    if tier == 'eligible-free':
        if environment.get('AIR_SDK_LICENSE_BASE64'):
            raise ValueError('Select paid when supplying a paid AIR licence.')
        return 'Owner confirms company turnover below US$50,000; required branding is retained.'
    if tier == 'paid' and environment.get('AIR_SDK_LICENSE_BASE64'):
        return 'Owner confirms appropriate paid AIR licence and CI coverage; SDK validates the licence.'
    raise ValueError('AIR SDK use is blocked: confirm eligible-free (company turnover below US$50,000) '
                     'or paid with AIR_SDK_LICENSE_BASE64. Internal use is not an exemption.')


if __name__ == '__main__':
    try:
        print(check(os.environ))
    except ValueError as error:
        print(error, file=sys.stderr)
        sys.exit(1)
