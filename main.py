# Created by BaiJiFeiLong@gmail.com at 2022/1/4 15:27

import ast

import astor
from pathlib3x import Path

gg = lambda x: x
Path("target").unlink(missing_ok=True)
root = Path("target") / "PySide2Stubs"
(root / "shiboken2").mkdir(parents=True, exist_ok=True)
(root / "shiboken2" / "__init__.pyi").write_text("class Object(object): ...")
(root / "PySide2").mkdir(parents=True, exist_ok=True)
(root / "PySide2" / "__init__.pyi").touch(exist_ok=True)
(root / "PySide2" / "support" / "signature" / "mapping").mkdir(parents=True, exist_ok=True)
(root / "PySide2" / "support" / "signature" / "typing").mkdir(parents=True, exist_ok=True)
(root / "PySide2" / "support" / "__init__.pyi").touch(exist_ok=True)
(root / "PySide2" / "support" / "signature" / "__init__.pyi").touch(exist_ok=True)
(root / "PySide2" / "support" / "signature" / "typing" / "__init__.pyi").touch(exist_ok=True)
mappings = [f"class {x}(object):..." for x in "Virtual,Missing,Invalid,Default,Instance".split(",")]
(root / "PySide2" / "support" / "signature" / "mapping" / "__init__.pyi").write_text("\n".join(mappings))

for moduleName in ["QtCore", "QtGui", "QtWidgets", "QtMultimedia"]:
    print(f"Processing module {moduleName}...")
    text = Path(f"./venv/Lib/site-packages/PySide2/{moduleName}.pyi").read_text()
    tree: ast.Module = ast.parse(text)

    nodes = tree.body[:]
    classes = [x for x in nodes if isinstance(x, ast.ClassDef) and x.name != "Object"]
    functions = [x for x in nodes if isinstance(x, ast.FunctionDef)]
    commons = [x for x in nodes if x not in gg(classes) + gg(functions)]

    for func in functions:
        func.decorator_list = [x for x in func.decorator_list if not isinstance(x, ast.Name)]

    (root / "PySide2" / moduleName).mkdir(exist_ok=True)
    modulePyi = root / "PySide2" / moduleName / "__init__.pyi"
    functionsPyi = root / "PySide2" / moduleName / "_functions.pyi"
    functionsPyi.write_text(astor.to_source(ast.Module(body=commons + functions)))
    imports = [f"from ._functions import {x.name} as {x.name}" for x in functions]

    for clazz in classes[:]:
        print(f"Processing class {moduleName}.{clazz.name}...")
        path = root / "PySide2" / moduleName / f"_{clazz.name}.pyi"
        path.write_text(astor.to_source(ast.Module(body=commons + [clazz])))
        imports.append(f"from ._{clazz.name} import {clazz.name} as {clazz.name}")
    modulePyi.write_text("\n".join(imports))
