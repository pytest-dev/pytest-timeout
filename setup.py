from setuptools import setup


setup(name='pytest-timeout',
      description='pytest plugin to abort tests after a timeout',
      long_description=open("README").read(),
      version='0.1',
      author='Floris Bruynooghe',
      author_email='flub@devork.be',
      url='http://bitbucket.org/flub/pytest-timeout/',
      license='MIT',
      py_modules=['pytest_timeout'],
      entry_points={'pytest11': ['timeout = pytest_timeout']},
      install_requires=['pytest>=2.0'],
      classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: Plugins',
        'Intended Audience :: Developers',
        'License :: DFSG approved',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Testing'])
