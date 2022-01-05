# Created by BaiJiFeiLong@gmail.com at 2022/1/4 15:27

import ast
import logging
import typing

import astor
import colorlog
import html2text
import pydash
from parsel import Selector
from pathlib3x import Path


def main():
    initLogging()
    failedClasses = []
    failedMethods = []
    docRoot = Path("~/scoop/persist/zeal/docsets/Qt_5.docset/Contents/Resources/Documents/doc.qt.io/qt-5").expanduser()
    stubRoot = Path("target") / "PySide2Stubs" / "PySide2"

    assert docRoot.exists()
    stubRoot.rmtree(ignore_errors=True)
    stubRoot.mkdir(parents=True)
    (stubRoot / "__init__.pyi").touch()

    for moduleName in ["QtCore", "QtGui", "QtWidgets", "QtMultimedia"][:1]:
        logging.info("Processing module %s...", moduleName)
        (stubRoot / moduleName).mkdir()
        moduleText = Path(f"./venv/Lib/site-packages/PySide2/{moduleName}.pyi").read_text()
        moduleText = moduleText.replace("Shiboken.Object", "object")

        statements = ast.parse(moduleText).body
        classes = [x for x in statements if isinstance(x, ast.ClassDef) and x.name != "Object"]
        functions = [x for x in statements if isinstance(x, ast.FunctionDef)]
        headers = statementsToHeaders(statements)

        for func in functions:
            func.decorator_list = [x for x in func.decorator_list if not isinstance(x, ast.Name)]
        functionsPyi = stubRoot / moduleName / "_functions.pyi"
        functionsPyi.write_text(astor.to_source(ast.Module(body=headers + gg(functions))))

        imports = [f"from ._functions import {x.name} as {x.name}" for x in functions]
        for clazz in classes:
            logging.info("Processing class %s.%s ...", moduleName, clazz.name)
            imports.append(f"from ._{clazz.name} import {clazz.name} as {clazz.name}")
            basename = clazz.name.lower().replace("::", "-").replace("_", "-") + ".html"
            if not (docRoot / basename).exists():
                failedClasses.append(clazz.name)
                continue
            html = (docRoot / basename).read_text(encoding="utf8")
            selector = Selector(html)
            signalsXpath = "//h2[@id='signals']/following-sibling::div[1]//td[2]/b/a[1]/text()"
            signalNames = [x.get() for x in selector.xpath(signalsXpath)]
            signalTemplate = "@property\ndef {}(self) -> PySide2.QtCore.SignalInstance: ..."
            for signalName in signalNames:
                signalCode = signalTemplate.format(signalName)
                signalMethod = ast.parse(signalCode).body[0]
                clazz.body.append(signalMethod)
            methods = [x for x in clazz.body if isinstance(x, ast.FunctionDef)]
            dkt = parseFunctions(selector)
            for method in methods:
                name = clazz.name if method.name == "__init__" else method.name
                logging.info("\tProcessing function %s.%s.%s", moduleName, clazz.name, name)
                possibleNames = calcPossibleNames(name)
                validNames = [x for x in possibleNames if x in dkt]
                if not validNames:
                    logging.warning("\t\tNo document found for this method.")
                    failedMethods.append(f"{clazz.name}.{name} {basename}")
                    continue
                paragraphs = dkt[validNames[0]]
                paragraphs = [x for x in paragraphs if x]
                logging.info("\t\tFound document with %d paragraphs", len(paragraphs))
                method.body.insert(0, ast.Expr(value=ast.Str(s=joinParagraphs(paragraphs, 2))))

        modulePyi = stubRoot / moduleName / "__init__.pyi"
        modulePyi.write_text("\n".join(imports), encoding="utf8")
        for clazz in classes:
            classPyi = stubRoot / moduleName / f"_{clazz.name}.pyi"
            classPyi.write_text(astor.to_source(ast.Module(body=headers + gg([clazz]))), encoding="utf8")

    logging.info("Failed classes:")
    for x in failedClasses:
        logging.info("\t%s", x)
    logging.info("Failed functions:")
    for x in failedMethods:
        logging.info("\t%s", x)


def joinParagraphs(paragraphs, indentLevel):
    text = f"\n\n{' ' * indentLevel * 4}".join(paragraphs)
    text = f"\n{' ' * indentLevel * 4}{text}\n        "
    return text


def initLogging():
    consoleLogPattern = "%(log_color)s%(asctime)s %(levelname)8s %(name)-16s %(message)s"
    logging.getLogger().handlers = [logging.StreamHandler()]
    logging.getLogger().handlers[0].setFormatter(colorlog.ColoredFormatter(consoleLogPattern))
    logging.getLogger().setLevel(logging.DEBUG)


def parseFunctions(selector):
    dumper = html2text.HTML2Text()
    dumper.ignore_tables = True
    dumper.body_width = 2 ** 31 - 1
    xpath = "//div[@class='prop' or @class='func']/*"
    dkt = dict()
    name = None
    for x in selector.xpath(xpath):
        tag = x.xpath("name()").get()
        if tag == "h3":
            name = x.attrib["id"]
            dkt[name] = []
        elif len(dkt):
            assert name
            text = dumper.handle(x.get()).strip()
            assert text or x.xpath("name()").get() == "a"
            text and dkt[name].append(text)
    assert all(dkt.values())
    return dkt


def gg(x) -> typing.Any:
    return x


def calcPossibleNames(name):
    names = [name, pydash.lower_first(pydash.trim_start(name, "set"))]
    names = list(dict.fromkeys(names))
    names = pydash.flatten([[x, f"{x}-prop", f"{x}-1"] for x in names])
    return names


def remove_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text


def uncapitalize(s):
    return s[:1].lower() + s[1:]


def statementsToHeaders(statements):
    statements = [x for x in statements if isinstance(x, ast.Import)]
    statements = [x for x in statements if x.names[0].name.startswith("PySide2")]
    statements = [ast.Import(names=[ast.alias(name="typing", asname=None)])] + statements
    statements = statements + gg([ast.Assign(targets=[ast.Name(id="bytes")], value=ast.Name(id="str"))])
    return statements


if __name__ == '__main__':
    main()
