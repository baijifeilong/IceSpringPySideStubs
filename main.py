# Created by BaiJiFeiLong@gmail.com at 2022/1/4 15:27

import ast
import re

import astor
import html2text
from parsel import Selector
from pathlib3x import Path

Path("target").rmtree(ignore_errors=True)
stubRoot = Path("target") / "PySide2Stubs"
(stubRoot / "shiboken2").mkdir(parents=True, exist_ok=True)
(stubRoot / "shiboken2" / "__init__.pyi").write_text("class Object(object): ...")
(stubRoot / "PySide2").mkdir(parents=True, exist_ok=True)
(stubRoot / "PySide2" / "__init__.pyi").touch(exist_ok=True)
(stubRoot / "PySide2" / "support" / "signature" / "mapping").mkdir(parents=True, exist_ok=True)
(stubRoot / "PySide2" / "support" / "signature" / "typing").mkdir(parents=True, exist_ok=True)
(stubRoot / "PySide2" / "support" / "__init__.pyi").touch(exist_ok=True)
(stubRoot / "PySide2" / "support" / "signature" / "__init__.pyi").touch(exist_ok=True)
(stubRoot / "PySide2" / "support" / "signature" / "typing" / "__init__.pyi").touch(exist_ok=True)
mappings = [f"class {x}(object): ..." for x in "Virtual,Missing,Invalid,Default,Instance".split(",")]
(stubRoot / "PySide2" / "support" / "signature" / "mapping" / "__init__.pyi").write_text("\n".join(mappings))

gg = lambda x: x
signalRegex = re.compile(r"^void (\w+)\(.*\)$")
docRoot = Path("~/scoop/persist/zeal/docsets/Qt_5.docset/Contents/Resources/Documents/doc.qt.io/qt-5").expanduser()
htmlDumper = html2text.HTML2Text()
htmlDumper.ignore_links = True
htmlDumper.ignore_emphasis = True
htmlDumper.ignore_tables = True
htmlDumper.body_width = 2 ** 31 - 1
signalTemplate = """
class Dummy(object):
    @property
    def signal(self) -> PySide2.QtCore.SignalInstance:
        \"\"\"
        **C++ Signature**: *signature*
        \"\"\"
        ...
"""
failed = []
for moduleName in ["QtCore", "QtGui", "QtWidgets", "QtMultimedia"]:
    print(f"Processing module {moduleName}...")
    text = Path(f"./venv/Lib/site-packages/PySide2/{moduleName}.pyi").read_text()
    tree: ast.Module = ast.parse(text)

    nodes = tree.body[:]
    classes = [x for x in nodes if isinstance(x, ast.ClassDef) and x.name != "Object"]
    functions = [x for x in nodes if isinstance(x, ast.FunctionDef)]
    commons = [x for x in nodes if x not in gg(classes) + gg(functions)]
    commons += ast.parse("bytes = str").body

    for func in functions:
        func.decorator_list = [x for x in func.decorator_list if not isinstance(x, ast.Name)]

    (stubRoot / "PySide2" / moduleName).mkdir(exist_ok=True)
    modulePyi = stubRoot / "PySide2" / moduleName / "__init__.pyi"
    functionsPyi = stubRoot / "PySide2" / moduleName / "_functions.pyi"
    functionsPyi.write_text(astor.to_source(ast.Module(body=commons + functions)))
    imports = [f"from ._functions import {x.name} as {x.name}" for x in functions]

    isEnum = lambda clz: all([isinstance(x, ast.AnnAssign) for x in clz.body])
    for clazz in classes[:]:
        print(f"Processing class {moduleName}.{clazz.name} (enum={isEnum(clazz)})...")
        path = stubRoot / "PySide2" / moduleName / f"_{clazz.name}.pyi"
        imports.append(f"from ._{clazz.name} import {clazz.name} as {clazz.name}")
        if clazz.name.startswith("Q") and not isEnum(clazz):
            basename = clazz.name.lower().replace("::", "-").replace("_", "-") + ".html"
            if not (docRoot / basename).exists():
                failed.append(clazz.name)
                html = ""
            else:
                html = (docRoot / basename).read_text(encoding="utf8")
            rows = Selector(html).xpath("//h2[@id='signals']/following-sibling::div[1]//tr")
            for row in rows:
                signature = htmlDumper.handle(row.get()).strip()
                name = signalRegex.match(signature).group(1)
                print("\tProcessing signal", name, "\t|\t", signature)
                signalCode = signalTemplate.replace("signal", name).replace("signature", signature)
                signalMethod = gg(ast.parse(signalCode).body[0]).body[0]
                clazz.body.append(signalMethod)
        path.write_text(astor.to_source(ast.Module(body=commons + [clazz])))
    modulePyi.write_text("\n".join(imports))

print("Failed:")
for x in failed:
    print("\t", x)
