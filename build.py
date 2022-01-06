# Created by BaiJiFeiLong@gmail.com at 2022/1/6 12:46

import distutils.log
import os

import setuptools.dist
from pathlib3x import Path

os.chdir(Path(__file__).parent / "target/PySide2Stubs")
for path in Path(".").glob("*"):
    if not path.stem.endswith("-stubs"):
        path.rmtree()

readme = Path("../../README.md").read_text(encoding="utf8")
distutils.log.set_verbosity(0)
for command in ["sdist", "bdist_wheel"]:
    setuptools.dist.Distribution(attrs=dict(
        script_name="",
        name='IceSpringPySideStubs-PySide2',
        url="https://github.com/baijifeilong/IceSpringPySideStubs",
        license='GPL3',
        author='BaiJiFeiLong',
        author_email='baijifeilong@gmail.com',
        version='1.0.3',
        description='PySide2 stubs with Qt signals and Qt documentations and more',
        packages=["PySide2-stubs"],
        package_data={"PySide2-stubs": ['*.pyi', '**/*.pyi']},
        long_description=readme,
        long_description_content_type='text/markdown'
    )).run_command(command)
