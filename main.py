# Created by BaiJiFeiLong@gmail.com at 2022/1/4 15:27

import ast
import importlib.util
import logging
import typing

import astor
import cacheout
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
        headers = parseModuleHeaders(statements)

        logging.info("Processing functions")
        for func in functions:
            logging.info(f"{' ' * 4}Processing function %s.%s", moduleName, func.name)
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

            logging.info("Processing class document")
            selector = Selector((docRoot / basename).read_text(encoding="utf8"))
            classDocuments = parseClassDocuments(selector)
            clazz.body.insert(0, ast.Expr(value=ast.Str(s=joinParagraphs(classDocuments, 1))))

            logging.info("Processing signals")
            signalsXpath = "//h2[@id='signals']/following-sibling::div[1]//td[2]/b/a[1]/text()"
            signalNames = [x.get() for x in selector.xpath(signalsXpath)]
            signalTemplate = "@property\ndef {}(self) -> PySide2.QtCore.SignalInstance: ..."
            for signalName in signalNames:
                logging.info(f"{' ' * 4}Processing signal: %s.%s.%s", moduleName, clazz.name, signalName)
                signalCode = signalTemplate.format(signalName)
                signalMethod = ast.parse(signalCode).body[0]
                clazz.body.append(signalMethod)

            logging.info("Processing methods")
            methods = [x for x in clazz.body if isinstance(x, ast.FunctionDef)]
            documentDict = parseFunctionDocuments(selector)
            for method in methods:
                name = clazz.name if method.name == "__init__" else method.name
                logging.info(f"{' ' * 4}Processing method %s.%s.%s", moduleName, clazz.name, name)
                possibleNames = calcPossibleNames(name)
                validNames = [x for x in possibleNames if x in documentDict]
                if not validNames:
                    logging.warning(f"{' ' * 8}No document found for this method.")
                    failedMethods.append(f"{clazz.name}.{name} {basename}")
                    continue
                documentEntry = documentDict[validNames[0]]
                signature = documentEntry["signature"]
                paragraphs = documentEntry["documents"]
                logging.info(f"{' ' * 8}Signature: %s", signature)
                logging.info(f"{' ' * 8}Found document with %d paragraphs", len(paragraphs))
                documents = [signature] + paragraphs
                method.body.insert(0, ast.Expr(value=ast.Str(s=joinParagraphs(documents, 2))))

        modulePyi = stubRoot / moduleName / "__init__.pyi"
        modulePyi.write_text("\n".join(imports), encoding="utf8")
        for clazz in classes:
            classPyi = stubRoot / moduleName / f"_{clazz.name}.pyi"
            classPyi.write_text(astor.to_source(ast.Module(body=headers + gg([clazz]))), encoding="utf8")

    logging.info("Failed classes:")
    for x in failedClasses:
        logging.warning("\t%s", x)
    logging.info("Failed functions:")
    for x in failedMethods:
        logging.warning("\t%s", x)


def joinParagraphs(paragraphs, indentLevel):
    paragraphs = [f"\n".join([f"{' ' * indentLevel * 4}{y}" for y in x.splitlines()]) for x in paragraphs]
    return "\n" + "\n\n".join(paragraphs) + f"\n{' ' * indentLevel * 4}"


def initLogging():
    consoleLogPattern = "%(log_color)s%(asctime)s %(levelname)8s %(name)-16s %(message)s"
    logging.getLogger().handlers = [logging.StreamHandler()]
    logging.getLogger().handlers[0].setFormatter(colorlog.ColoredFormatter(consoleLogPattern))
    logging.getLogger().setLevel(logging.DEBUG)


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
    return parser


@cacheout.memoize()
def getSignatureParser() -> html2text.HTML2Text:
    parser: html2text.HTML2Text = html2text.HTML2Text()
    parser.body_width = 2 ** 31 - 1
    parser.ignore_links = True
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
            signature = f"**{signature}**"
            dkt[name] = dict(
                signature=signature,
                documents=[]
            )
        elif len(dkt):
            assert name
            text = getDocumentParser().handle(x.get()).replace("also**", "also** ").strip()
            text = text.replace("*>", "\\*>")
            assert text or x.xpath("name()").get() == "a"
            text and dkt[name]["documents"].append(text)
    assert all(x["documents"] for x in dkt.values())
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
    names = [name, pydash.lower_first(pydash.trim_start(name, "set"))]
    names = list(dict.fromkeys(names))
    names = pydash.flatten([[x, f"{x}-prop", f"{x}-1"] for x in names])
    return names


def parseModuleHeaders(statements):
    statements = [x for x in statements if isinstance(x, ast.Import)]
    statements = [x for x in statements if x.names[0].name.startswith("PySide2")]
    statements = [ast.Import(names=[ast.alias(name="typing", asname=None)])] + statements
    statements = statements + gg([ast.Assign(targets=[ast.Name(id="bytes")], value=ast.Name(id="str"))])
    return statements


if __name__ == '__main__':
    main()
