from setuptools import setup
import libtivomind

setup(name='libtivomind',
      version=libtivomind.__version__,
      description='A library that handles the RPC connection to a '
                  'TiVo using the Mind RPC protocal.',
      author='Michael Uhl',
      url='https://github.com/michaeluhl/libtivomind',
      license='LGPL',
      packages=['libtivomind'],
      classifiers=[
          'Development Status :: 4 - Beta',
          'Environment :: Other Environment',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
          'Operating System :: OS Independent',
          'Programming Language :: Python :: 3 :: Only',
          'Topic :: Software Development :: Libraries :: Application Frameworks',
          ],
      zip_safe=True)
