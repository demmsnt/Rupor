from setuptools import setup, find_packages
from os.path import join, dirname

setup(
    name='patch_admin',
    long_description=open(join(dirname(__file__), 'README.rst')).read(),
    include_package_data=True,
    description='Rupor --- Simple pupsub chat',
    version='0.1',
    classifiers=[
        "Operating System :: POSIX",
        "Programming Language :: Python :: 3.5",
        "Topic :: Internet :: WWW/HTTP",
    ],
    url='https://localhost/',
    keywords=['asyncio', 'aiohttp'],
    packages=find_packages(),
    package_data={
        'templates': ['*.html'],
    },
    install_requires=[
        'aiohttp == 3.4.4',
        'filemagic',
        'jinja2',
        'PyYAML == 3.13',
        'dpath == 1.4.2'
    ],
    dependency_links=[
    ],
    entry_points={
        'console_scripts': [
            'rupor=rupor.main:main',
        ],
    },
)
