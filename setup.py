from setuptools import setup
import codecs


def read(filename):
    return codecs.open(filename, encoding='utf-8').read()


long_description = '\n\n'.join([read('README'),
                                read('AUTHORS'),
                                read('CHANGES')])

setup(
    name='lantzdev',
    version='0.6.2',
    license='BSD 3-Clause License',
    description='Simple yet powerful instrumentation in Python',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/lantzproject/lantz',
    author='Hernan E. Grecco',
    author_email='hernan.grecco@gmail.com',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Operating System :: Unix',
        'Operating System :: MacOS :: MacOS X',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Scientific/Engineering',
        'Topic :: Scientific/Engineering :: Interface Engine/Protocol Translator',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: User Interfaces',
        'Topic :: Software Development :: Widget Sets',
        'Topic :: System :: Hardware',
        'Topic :: System :: Hardware :: Hardware Drivers',
        'Topic :: System :: Logging',
        'Topic :: System :: Monitoring',
        'Topic :: Utilities',
    ],
    keywords='lantz, hardware interface, instrumentation framework, science, research',
    packages=['lantz', 'lantz.core'],
    zip_safe=False,
    python_requires='>=3.6, <4',
    install_requires=[
        'pimpmyclass>=0.4.3',
        'pint>=0.16',
        'pyvisa>=1.10.1',
        'pysignal>=1.1.1',
        'pyyaml>=5.3.1',
        'serialize>=0.1',
        'stringparser>=0.5',
    ],
    extras_require={
        'qt': [
            'lantz-qt>=0.6',
        ],
        'ino': [
            'lantz-ino>=0.6',
        ],
        'full': [
            'lantz-qt>=0.6',
            'lantz-ino>=0.6',
        ],
        'color': [
            'colorama>=0.4.3',
        ],
    },
    entry_points={
        'console_scripts': [
            'lantz = lantz.__main__:main',
            'lantz-config = lantz.core.__main__:config',
        ],
        'lantz_subcommands': [
            'config = lantz.core.__main__:config',
        ],
    },
    test_suite='lantz.core.testsuite.testsuite',
    project_urls={
        'Bug Reports': 'https://github.com/lantzproject/lantz/issues',
        'Source': 'https://github.com/lantzproject/lantz/',
    },
    include_package_data=True,
    options={'bdist_wheel': {'universal': '1'}},
)
