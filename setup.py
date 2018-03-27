import os

from setuptools import setup, find_packages

# pypi doesn't like markdown, it needs RST.
# https://stackoverflow.com/questions/26737222/pypi-description-markdown-doesnt-work
try:
    import pypandoc
    long_description = pypandoc.convert('README.md', 'rst')
except:
    long_description = open('README.md').read()

setup(
    name = 'pretix-checkinlist-net',
    version = '1.0.0',
    description = 'Pretix checkin list exporter for NETWAYS',
    long_description = long_description,
    url = 'https://github.com/NETWAYS/pretix-checkinlist-net',
    download_url = 'https://github.com/NETWAYS/pretix-invoice-net/archive/v1.0.0.tar.gz',
    keywords = [ 'pretix', 'tickets', 'events', 'invoice', 'pdf' ],
    author = 'NETWAYS GmbH',
    author_email = 'support@netways.de',
    license = 'Apache Software License',

    # pretix already depends on checkin related packages
    install_requires = [],
    packages = find_packages(exclude=['tests', 'tests.*']),
    include_package_data = True,
    entry_points = """
[pretix.plugin]
pretix_checkinlist_net=pretix_checkinlist_net:PretixPluginMeta
""",
)
