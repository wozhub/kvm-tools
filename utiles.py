
from os.path import join
from os import walk, remove, rmdir
from gzip import open as gzipOpen
from os import remove as osRemove


def borrarArbol(top):
    # http://docs.python.org/2/library/os.html  ->  os.walk example
    for root, dirs, files in walk(top, topdown=False):
        for archivo in files:
            remove(join(root, archivo))
        for directorio in dirs:
            rmdir(join(root, directorio))
    rmdir(top)


def comprimirArchivo(self, archivo):
    print "Comprimiendo %s" % archivo

    try:
        f_in = open(archivo, 'rb')
        f_out = gzipOpen(archivo+'.gz', 'wb')
        f_out.writelines(f_in)
        f_out.close()
        f_in.close()
        osRemove(archivo)
    except:
        pass
