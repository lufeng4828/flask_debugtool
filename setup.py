import os
from setuptools import setup, find_packages


here = os.path.abspath(os.path.dirname(__file__))

try:
    README = open(os.path.join(here, 'README.rst')).read()
    CHANGES = open(os.path.join(here, 'CHANGES.rst')).read()
except:
    README = ''
    CHANGES = ''


setup(
    name='Flask-DebugTool',
    version='0.1.0',
    license='BSD',
    author='Feng Lu',
    author_email='lufeng044@qq.com',
    maintainer='Feng Lu',
    maintainer_email='lufeng044@qq.com',
    description='A toolbar overlay for debugging Flask applications.',
    long_description=README + '\n\n' + CHANGES,
    zip_safe=False,
    platforms='any',
    include_package_data=True,
    packages=['flask_debugtool',
              'flask_debugtool.panels'
    ],
    install_requires=[
        'Flask>=0.8',
        'Blinker',
        'itsdangerous',
        'werkzeug',
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
