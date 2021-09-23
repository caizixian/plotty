"""
WSGI config for foobar project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.11/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ["DJANGO_SETTINGS_MODULE"] = "plotty.settings"

os.environ['PLOTTY_ROOT'] = os.path.abspath(os.path.join(__file__, os.pardir, os.pardir, os.pardir, os.pardir))

application = get_wsgi_application()
