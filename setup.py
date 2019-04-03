import setuptools

with open('README.md', 'r') as fin:
    long_description=fin.read()
exec(open('MeiTingTrunk/version.py').read())

setuptools.setup(
        name='meitingtrunk',
        version=__version__,
        author='Guangzhi XU',
        author_email='xugzhi1987@gmail.com',
        description='An open source reference management tool developed in PyQt5 and Python3.',
        long_description=long_description,
        long_description_content_type='text/markdown',
        url='https://github.com/Xunius/MeiTingTrunk',
        packages=setuptools.find_packages(),
        classifiers=[
            'Development Status :: 3 - Alpha',
            'Environment :: X11 Applications :: Qt',
            'Intended Audience :: End Users/Desktop',
            'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
            'Natural Language :: English',
            'Operating System :: POSIX :: Linux',
            'Operating System :: MacOS',
            'Programming Language :: Python :: 3',
            'Topic :: Education'
            ],
        install_requires=[
            #'qt>=5',
            'PyQt5',
            'pdfminer.six',
            'pypdf2',
            'beautifulsoup4',
            'fuzzywuzzy',
            'bibtexparser',
            'crossrefapi',
            'RISparser',
            'send2trash'
            ],
        python_requires='>=3',
        #package_data={'sample': ['
        entry_points={
            'gui_scripts': ['meitingtrunk = MeiTingTrunk.main:main']
            }
        )
