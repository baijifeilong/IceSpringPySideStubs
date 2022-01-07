# Created by BaiJiFeiLong@gmail.com at 2022/1/6 12:46

import distutils.log
import logging
import os

import colorlog
import setuptools.dist
from pathlib3x import Path


def main():
    initLogging()
    for binding in ["PySide2", "PySide6", "PyQt5"]:
        logging.info("Building for binding %s...", binding)
        processBinding(binding)
    logging.info("Generated files:")
    for path in Path("target").glob("**/dist/*"):
        logging.info(f"\t{path} %.2f MB", path.stat().st_size / 1024 / 1024)


def initLogging():
    consoleLogPattern = "%(log_color)s%(asctime)s %(levelname)8s %(name)-16s %(message)s"
    logging.getLogger().handlers = [logging.StreamHandler()]
    logging.getLogger().handlers[0].setFormatter(colorlog.ColoredFormatter(consoleLogPattern))
    logging.getLogger().setLevel(logging.DEBUG)


def processBinding(binding: str):
    readme = Path("README.md").read_text(encoding="utf8")
    os.chdir(f"target/{binding}Stubs")
    for path in Path().glob("*"):
        if not path.stem.endswith("-stubs"):
            path.rmtree()

    distutils.log.set_verbosity(1)
    for command in ["sdist", "bdist_wheel"]:
        setuptools.dist.Distribution(attrs=dict(
            script_name="",
            name=f'IceSpringPySideStubs-{binding}',
            url="https://github.com/baijifeilong/IceSpringPySideStubs",
            license='GPLv3',
            author='BaiJiFeiLong',
            author_email='baijifeilong@gmail.com',
            version='1.2.0',
            description=f'{binding} stubs with Qt signals and Qt documentations and more',
            packages=[f"{binding}-stubs"],
            package_data={f"{binding}-stubs": ['*.pyi', '**/*.pyi']},
            long_description=readme,
            long_description_content_type='text/markdown'
        )).run_command(command)
    os.chdir("../..")


if __name__ == '__main__':
    main()
