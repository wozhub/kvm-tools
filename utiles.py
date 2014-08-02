
from os.path import join
from os import walk, remove, rmdir


def borrarArbol(top):
    # http://docs.python.org/2/library/os.html  ->  os.walk example
    for root, dirs, files in walk(top, topdown=False):
        for archivo in files:
            remove(join(root, archivo))
        for directorio in dirs:
            rmdir(join(root, directorio))
    rmdir(top)
