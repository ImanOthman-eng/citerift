"""Add python_functions = [one name per (file, suite)] to pyproject.toml. Usage: narrow_pyproject.py NAMESFILE PYPROJECT"""
import sys
names = [l.strip() for l in open(sys.argv[1]) if l.strip()]
s = open(sys.argv[2]).read()
s = s.replace("xfail_strict = true", "xfail_strict = true\npython_functions = " + repr(names).replace("'", '"'))
open(sys.argv[2], "w").write(s)
