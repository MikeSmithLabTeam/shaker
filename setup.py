import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("LICENSE", "r") as fh:
    license = fh.read()

setuptools.setup(
    name='shaker',
    version='1.0.0',
    license=license,
    packages=setuptools.find_packages(
        exclude=('tests', 'docs')
    ),
    url='https://github.com/MikeSmithLabTeam/shaker',
    install_requires=[
        'ipykernel',
        'tqdm',
        'opencv-python',
        'pywin32',
        'numpy',
        'pandas',
        'matplotlib',
        'scipy',
        'typing',
        'labvision @ git+https://github.com/mikesmithlabteam/labvision',
        'labequipment @ git+https://github.com/MikeSmithLabTeam/labequipment',
        'skopt @ git+https://github.com/MikeSmithLabTeam/skopt',
    ],
    test_suite='nose.collector',
    tests_require=['nose'],
    include_package_data=True,
)
