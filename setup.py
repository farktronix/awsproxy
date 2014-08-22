from distutils.core import setup

setup(
    name='AWSProxy',
    version='0.1.0',
    author='Jacob Farkas',
    author_email='jacobf@rkas.net',
    packages=['awsproxy'],
    scripts=[],
    url='https://github.com/farktronix/awsproxy',
    license='LICENSE.txt',
    description='On-demand AWS-based proxy.',
    long_description=open('README.md').read(),
    install_requires=[
        "Boto >= 2.32.1",
    ],
)
