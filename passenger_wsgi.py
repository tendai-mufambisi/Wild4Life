import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "w4l_donations.settings")

from w4l_donations.wsgi import application
