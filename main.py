# Created by BaiJiFeiLong@gmail.com at 2022/1/4 15:27

import ast
import concurrent.futures
import importlib.util
import logging
import os
import re
import textwrap
import typing

import astor
import autoflake
import black
import cacheout
import colorlog
import html2text
import psutil
import pydash
from IceSpringPathLib import Path
from parsel import Selector


def main():
    initLogging()
    futures = dict()
    bindings = ["PySide2", "PySide6", "PyQt5", "PyQt6"]
    executor = concurrent.futures.ProcessPoolExecutor(max_workers=len(bindings))
    logging.info("Start works: %s", ", ".join(bindings))
    for binding in bindings[:]:
        futures[executor.submit(processBinding, binding)] = binding
    for index, future in enumerate(concurrent.futures.as_completed(futures)):
        execOrKillSelf(lambda: future.result())
        logging.info("[%d] Child work %s completed", index + 1, futures[future])
    logging.info("All works completed: %s", ", ".join(bindings))


def execOrKillSelf(func, *args, **kwargs) -> None:
    try:
        func(*args, **kwargs)
    except Exception as e:
        logging.error("Exception occurred: %s", repr(e), exc_info=True)
        for process in psutil.Process(os.getpid()).children(recursive=True) + [psutil.Process(os.getpid())]:
            process.kill()


def processBinding(binding: str):
    initLogging()
    logging.info("Processing binding %s...", binding)
    qtVersion = dict(PySide2=5, PySide6=6, PyQt5=5, PyQt6=6)[binding]
    docFilenames = dict(
        Qt5="~/scoop/persist/zeal/docsets/Qt_5.docset/Contents/Resources/Documents/doc.qt.io/qt-5",
        Qt6="~/scoop/persist/zeal/docsets/Qt_6.docset/Contents/Resources/Documents/doc.qt.io/qt-6",
    )
    docRoot = Path(docFilenames[f"Qt{qtVersion}"]).expanduser()
    stubRoot = Path("target") / f"{binding}Stubs" / f"{binding}-stubs"

    assert docRoot.exists()
    stubRoot.rmtree(ignore_errors=True)
    stubRoot.mkdir(parents=True, exist_ok=True)
    (stubRoot / "__init__.pyi").touch()

    failedClasses = []
    failedMethods = []
    modulesNames = [x.stem for x in Path(f"./venv/Lib/site-packages/{binding}").glob("*.pyi")]
    for moduleName in modulesNames:
        logging.info("Processing module %s.%s...", binding, moduleName)
        (stubRoot / moduleName).mkdir(exist_ok=True)
        moduleText = Path(f"./venv/Lib/site-packages/{binding}/{moduleName}.pyi").read_text()
        moduleText = preprocessPyi(moduleText, binding)

        statements = ast.parse(moduleText).body
        classes = [x for x in statements if isinstance(x, ast.ClassDef) and x.name != "Object"]
        headers = parseModuleHeaders(binding, moduleName, statements)
        functions = [x for x in statements if isinstance(x, (ast.FunctionDef, ast.AnnAssign, ast.Assign))]

        logging.info("Processing functions")
        assignToName = lambda x: gg(x.targets[0]).id if isinstance(x, ast.Assign) else x.target.id
        funcToName = lambda x: x.name if isinstance(x, ast.FunctionDef) else assignToName(x)
        for func in functions:
            logging.info(f"{' ' * 4}Processing function %s.%s", moduleName, funcToName(func))
            if isinstance(func, ast.FunctionDef):
                func.decorator_list = [x for x in func.decorator_list if not isinstance(x, ast.Name)]
        functionsPyi = stubRoot / moduleName / "_functions.pyi"
        functionsPyi.write_text(prettyCode(astor.to_source(ast.Module(body=headers + gg(functions)))))
        imports = [f"from ._functions import {funcToName(x)} as {funcToName(x)}" for x in functions]

        for clazz in classes:
            logging.info("Processing class %s.%s.%s ...", binding, moduleName, clazz.name)
            imports.append(f"from ._{clazz.name} import {clazz.name} as {clazz.name}")
            basename = clazz.name.lower().replace("::", "-").replace("_", "-") + ".html"
            if not (docRoot / basename).exists():
                failedClasses.append(clazz.name)
                continue

            logging.info("Processing class document")
            selector = Selector((docRoot / basename).read_text())
            classDocuments = parseClassDocuments(selector)
            classUrl = f"https://doc.qt.io/qt-{qtVersion}/{basename}"
            classDocuments.insert(0, classUrl)
            clazz.body.insert(0, ast.Expr(value=ast.Str(s=joinParagraphs(classDocuments, 1))))

            logging.info("Processing signals")
            signalsXpath = "//h2[@id='signals']/following-sibling::div[1]//td[2]/b/a[1]/text()"
            signalNames = [x.get() for x in selector.xpath(signalsXpath)]
            signalTemplate = "@property\ndef {}(self) -> {}.QtCore.{}: ..."
            signalClassName = "SignalInstance" if binding.startswith("PySide") else "pyqtBoundSignal"
            clazz.body = [x for x in clazz.body if not (isinstance(x, ast.FunctionDef) and x.name in signalNames)]
            for signalName in signalNames:
                logging.info(f"{' ' * 4}Processing signal: %s.%s.%s", moduleName, clazz.name, signalName)
                signalCode = signalTemplate.format(signalName, binding, signalClassName)
                signalMethod = ast.parse(signalCode).body[0]
                clazz.body.append(signalMethod)

            logging.info("Processing methods")
            methods = [x for x in clazz.body if isinstance(x, ast.FunctionDef)]
            documentDict = parseFunctionDocuments(selector)
            usedNames = []
            for method in methods:
                name = clazz.name if method.name == "__init__" else method.name
                logging.info(f"{' ' * 4}Processing method %s.%s.%s", moduleName, clazz.name, name)
                possibleNames = calcPossibleNames(name)
                validNames = [x for x in possibleNames if x in documentDict]
                if not validNames:
                    logging.warning(f"{' ' * 8}No document found for this method.")
                    failedMethods.append(f"{clazz.name}.{name} {basename}")
                    continue
                unusedValidNames = [x for x in validNames if x not in usedNames]
                methodId = (unusedValidNames or validNames)[0]
                usedNames.append(methodId)
                documentEntry = documentDict[methodId]
                signature = documentEntry["signature"]
                paragraphs = documentEntry["documents"]
                logging.info(f"{' ' * 8}Signature: %s", signature)
                logging.info(f"{' ' * 8}Found document with %d paragraphs", len(paragraphs))
                documents = [signature] + paragraphs
                documents.insert(0, f"{classUrl}#{methodId}")
                method.body.insert(0, ast.Expr(value=ast.Str(s=joinParagraphs(documents, 2))))

        logging.info("Writing module %s.%s", binding, moduleName)
        modulePyi = stubRoot / moduleName / "__init__.pyi"
        modulePyi.write_text(prettyCode("\n".join(imports), keepImports=True))
        for clazz in classes:
            logging.info("Writing class %s.%s.%s ...", binding, moduleName, clazz.name)
            classPyi = stubRoot / moduleName / f"_{clazz.name}.pyi"
            classPyi.write_text(prettyCode(astor.to_source(ast.Module(body=headers + gg([clazz])),
                pretty_source=lambda x: "".join(x))))

    logging.info("Failed classes:")
    for x in failedClasses:
        logging.warning("\t%s", x)
    logging.info("Failed functions:")
    for x in failedMethods:
        logging.warning("\t%s", x)


def preprocessPyi(text: str, binding: str) -> str:
    if binding.startswith("PySide"):
        text = text.replace("Shiboken.Object", "object")
    elif binding.startswith("PyQt"):
        text = text.replace("class DiscoveryMethod(int):\n\n", "class DiscoveryMethod(int): ...\n\n")
        text = re.sub(r"(\w+)(\s*=\s*...\s*#\s*type:\s*)(\w+)", r"\1 : \3\2\3", text)
    return text


def joinParagraphs(paragraphs, indentLevel):
    paragraphs = [textwrap.fill(x, 80 - indentLevel * 4, replace_whitespace=False) for x in paragraphs if x.strip()]
    return "\n" + textwrap.indent("\n\n".join(paragraphs), ' ' * indentLevel * 4) + f"\n{' ' * indentLevel * 4}"


def initLogging():
    consoleLogPattern = "%(log_color)s%(asctime)s %(levelname)8s %(name)-16s %(message)s"
    logging.getLogger().handlers = [logging.StreamHandler()]
    logging.getLogger().handlers[0].setFormatter(colorlog.ColoredFormatter(consoleLogPattern))
    logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger("blib2to3.pgen2.driver").setLevel(logging.INFO)


@cacheout.memoize()
def getDocumentParser() -> html2text.HTML2Text:
    spec = importlib.util.find_spec("html2text", None)
    lines = spec.loader.get_source("html2text").splitlines()
    assert "self.o" in lines[834]
    lines[834] = ' ' * 16 + 'self.o("**")'
    assert "self.o" in lines[458]
    lines[458] = " " * 12 + 'self.o(title + "** ")'
    assert "self.o" in lines[339]
    lines[339] = " " * 16 + 'self.o("**")'
    assert "self.inheader" in lines[341]
    lines[341] = " " * 16 + 'self.inheader = False; self.o("**")'
    assert "self.p()" in lines[336]
    lines[336] = ""
    module = importlib.util.module_from_spec(spec)
    exec(compile("\n".join(lines), module.__spec__.origin, "exec"), module.__dict__)
    parser: html2text.HTML2Text = gg(module).HTML2Text()
    parser.ignore_tables = True
    parser.body_width = 2 ** 31 - 1
    parser.emphasis_mark = "**"
    return parser


@cacheout.memoize()
def getSignatureParser() -> html2text.HTML2Text:
    parser: html2text.HTML2Text = html2text.HTML2Text()
    parser.body_width = 2 ** 31 - 1
    parser.ignore_links = True
    parser.emphasis_mark = ""
    return parser


def parseFunctionDocuments(selector):
    xpath = "//div[@class='prop' or @class='func']/*"
    dkt = dict()
    name = None
    for x in selector.xpath(xpath):
        tag = x.xpath("name()").get()
        if tag == "h3":
            name = x.attrib["id"]
            signature = getSignatureParser().handle(x.get()).replace("###", "").strip()
            signature = f"**{signature}**".replace("`", "")
            dkt[name] = dict(signature=signature, documents=[])
        elif len(dkt):
            assert name
            text = getDocumentParser().handle(x.get()).replace("also**", "also** ").strip()
            text = text.replace("*>", "\\*>")
            assert text or x.xpath("name()").get() in ["a", "div"]
            text and dkt[name]["documents"].append(text)
    return dkt


def parseClassDocuments(selector):
    xpath = '//div[@class="descr"]/*|//div[@class="descr"]/following-sibling::p[1]'
    documents = [
        getDocumentParser().handle(x.get()).replace("also**", "also** ").strip() for x in selector.xpath(xpath)]
    assert documents
    return documents


def gg(x) -> typing.Any:
    return x


def calcPossibleNames(name):
    names = list(dict.fromkeys([name, pydash.lower_first(pydash.trim_start(name, "set")), pydash.trim_end(name, "_")]))
    names = pydash.flatten_deep([[x, f"{x}-prop", [f"{x}-{y + 1}" for y in range(10)]] for x in names])
    return names


def parseModuleHeaders(binding, module, statements):
    statements = [x.body[0] if isinstance(x, ast.Try) else x for x in statements]
    statements = [x for x in statements if not isinstance(x, (ast.ClassDef, ast.FunctionDef))]
    statements = [x for x in statements if not isinstance(x, (ast.Assign, ast.AnnAssign))]
    if binding.startswith("PySide"):
        statements = [x for x in statements if "shiboken" not in astor.to_source(x).lower()]
        statements = [x for x in statements if "PySide2.support.signature" not in astor.to_source(x)]
        for statement in statements:
            if isinstance(statement, ast.ImportFrom) and statement.module == "typing":
                statement.names.append(ast.alias(name="Iterable", asname=None))
        statements.append(ast.parse("bytes = str").body[0])
    elif binding.startswith("PyQt"):
        statements = gg([x for x in statements if isinstance(x, (ast.Import, ast.ImportFrom))]) + \
                     [ast.parse(f"from {binding}.{module} import *").body[0]] + \
                     ([ast.parse(f"from {binding} import sip").body[0]] if module != "sip" else []) + \
                     [ast.parse(f"import enum").body[0]] + \
                     [x for x in statements if not isinstance(x, (ast.Import, ast.ImportFrom))]
    return statements


def prettyCode(code: str, keepImports=False):
    code = autoflake.fix_code(code, remove_all_unused_imports=not keepImports)
    code = "\n".join([re.sub("(?<!\\\\)\\\\n", "\n", x) for x in code.splitlines()])
    code = black.format_str(code, mode=black.Mode())
    return "\n".join(['"""', "\n\n".join([
        "PySide stub files generated by **IceSpringPySideStubs**",
        "Home: https://baijifeilong.github.io/2022/01/06/ice-spring-pyside-stubs/index.html",
        "Github: https://github.com/baijifeilong/IceSpringPySideStubs",
        "PyPI(PySide2): https://pypi.org/project/IceSpringPySideStubs-PySide2",
        "PyPI(PySide6): https://pypi.org/project/IceSpringPySideStubs-PySide6",
        "PyPI(PyQt5): https://pypi.org/project/IceSpringPySideStubs-PyQt5",
        "PyPI(PyQt6): https://pypi.org/project/IceSpringPySideStubs-PyQt6",
        "Generated by BaiJiFeiLong@gmail.com",
        "License: MIT"
    ]), '"""']) + "\n" + code


if __name__ == '__main__':
    main()
