from setuptools import setup, find_packages

setup(name='credisuretl',
      version='0.1.9',
      description='ETL for Felsim',
      url='http://github.com/fedegos/credisuretl',
      author='Federico Gosman',
      author_email='federico@equipogsm.com',
      license='MIT',
      packages=find_packages(),
      entry_points={
          'console_scripts': [
              'credisur = credisur.__main__:main'
          ]
      },
      install_requires=[
            'openpyxl==2.4.7',
            'xlrd'
      ],
      zip_safe=False)