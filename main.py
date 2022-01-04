# Created by BaiJiFeiLong@gmail.com at 2022/1/4 15:27

import ast
import re

import astor
import html2text
from parsel import Selector
from pathlib3x import Path

docRoot = Path("~/scoop/persist/zeal/docsets/Qt_5.docset/Contents/Resources/Documents/doc.qt.io/qt-5").expanduser()
assert docRoot.exists()
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

dumper = html2text.HTML2Text()
dumper.ignore_tables = True
dumper.body_width = 2 ** 31 - 1


def parseFunctions(selector):
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
            dkt[name].append(dumper.handle(x.get()).strip())
    return dkt


def remove_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text  # or whatever


def uncapitalize(s):
    return s[:1].lower() + s[1:]


def findDocInDict(dkt, name):
    name2 = uncapitalize(remove_prefix(name, "set"))
    for x in [name, name + "-prop", "name" + "-1", name2, name2 + "-prop"]:
        if x in dkt:
            return dkt[x]
    return []


gg = lambda x: x
signalRegex = re.compile(r"^void (\w+)\(.*\)$")
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
docXpath = "//h3/following-sibling::*[preceding-sibling::h3[1][{}] and not(self::h3)]"
count = 0
failures = []
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
        print(f"\nProcessing class {moduleName}.{clazz.name} (enum={isEnum(clazz)})...")
        path = stubRoot / "PySide2" / moduleName / f"_{clazz.name}.pyi"
        imports.append(f"from ._{clazz.name} import {clazz.name} as {clazz.name}")
        basename = clazz.name.lower().replace("::", "-").replace("_", "-") + ".html"
        if not (docRoot / basename).exists():
            failed.append(clazz.name)
            html = ""
        else:
            html = (docRoot / basename).read_text(encoding="utf8")
        selector = Selector(html)
        rows = selector.xpath("//h2[@id='signals']/following-sibling::div[1]//tr")
        for row in rows:
            signature = htmlDumper.handle(row.get()).strip()
            name = signalRegex.match(signature).group(1)
            print("\tSignal", name, "\t|\t", signature)
            signalCode = signalTemplate.replace("signal", name).replace("signature", signature)
            signalMethod = gg(ast.parse(signalCode).body[0]).body[0]
            clazz.body.append(signalMethod)
        methods = [x for x in clazz.body if isinstance(x, ast.FunctionDef)]
        dkt = parseFunctions(selector)
        for method in methods:
            name = clazz.name if method.name == "__init__" else method.name
            print(f"\n\tFunction {clazz.name}.{name}")
            doc = findDocInDict(dkt, name)
            print("\n".join([f"\t\t{x}" for x in doc if x]))
            if doc:
                doc = "\n\n".join(doc)
                method.body.insert(0, ast.Expr(value=ast.Str(
                    s="\n" + "\n\n".join(f"        {x}" for x in doc.splitlines() if x) + "\n        ")))
            if html:
                if not doc:
                    count += 1
                    print(str(docRoot / basename))
                    failures.append(f"{clazz.name}.{name} {basename}")
                    if count >= 2500:
                        print()
                        for failure in failures:
                            print(failure)
        path.write_text(astor.to_source(ast.Module(body=commons + [clazz])), encoding="utf8")
        # html and exit()
    modulePyi.write_text("\n".join(imports), encoding="utf8")

print("Failed:")
for x in failed:
    print("\t", x)
print("\nFailures:")
for x in failures:
    print("\t", x)
