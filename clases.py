#!/usr/bin/python

from libvirt import open as libvirtOpen
from gzip import open as gzipOpen
from os import remove
from xml.dom.minidom import parseString
from time import sleep
from datetime import date
from os.path import exists
from os import makedirs, listdir

from ssh import ssh_wrapper
from utiles import borrarArbol

estados = {0: 'no state', 1: 'running', 2: 'blocked on resource',
           3: 'paused by user', 4: 'being shut down', 5: 'shut off',
           6: 'crashed', 7: 'suspended', 8: 'last'}


class kvmHost():
    def __init__(self, conf):

        self._configuracion = conf

        if conf['tipo'] is None:
            self.url = "qemu:///system"
            self.ssh = None
        else:
            self.url = "%s://%s@%s/system" % (conf['tipo'],
                                              conf['usuario'],
                                              conf['host'])

            self.ssh = ssh_wrapper(conf['host'], 22, conf['usuario'], "")
            # self.ssh = SSHClient()
            # self.ssh.set_missing_host_key_policy(AutoAddPolicy())

        self.libvirt = libvirtOpen(self.url)
        self._guests = []

    def __repr__(self):
        r = "%s" % self.url
        for g in self.guests():
            r += "\n\t%s" % g
        return r

    def guests(self):
        if self._guests == []:
            self._guests = self._getGuests()
        return self._guests

    def guestsIDs(self):
        return self.libvirt.listDomainsID()

    def guestsNames(self):
        guests = []
        for g in self.guestsIDs():
            guests.append(self.libvirt.lookupByID(g).name())
        guests += self.libvirt.listDefinedDomains()
        return guests

    def respaldo_completo(self):
        print "%s: Iniciando respaldo_completo" % self._configuracion['host']
        for g in self.guests():
            if g.name in self._configuracion['guests_excluidos']:
                print "%s esta excluido de los respaldos!" % g.name
            else:
                g.respaldar()

    def respaldo_selectivo(self, seleccion):
        print "%s: Iniciando respaldo_selectivo" % self._configuracion['host']
        for g in self.guests():
            if g.name in seleccion:
                g.respaldar()

    def limpiarRespaldos(self):
        print "%s: Limpiando respaldos antiguos" % self._configuracion['host']
        for g in self.guests():
            g.limpiarRespaldos()

    def _getGuest(self, guest_name):
        for g in self.guests():
            if g.name == guest_name:
                return g

    def _getGuests(self):
        guests = []
        for n in self.guestsNames():
            g = kvmGuest(self._configuracion, self.libvirt.lookupByName(n),
                         self.ssh, n)
            guests.append(g)
        return guests


class kvmGuest():
    def __init__(self, conf, libvirt, ssh, name):
        self._configuracion = conf
        self.libvirt = libvirt
        self.ssh = ssh
        self.name = name
        self._discos = []
        self.xml = libvirt.XMLDesc(0)

        fecha = date.today().isoformat()
        self.ruta_respaldos_base = "/".join([conf['ruta_respaldos'], name])
        self.ruta_respaldos = "/".join([conf['ruta_respaldos'], name, fecha])

    def __repr__(self):
        i, n = self.estado()
        r = "%s [%d,%s]" % (self.name, i, n)
        for d in self.discos():
            r += "\n\t\t%s" % d
        return r

    def estado(self):
        i = self.libvirt.info()[0]
        n = estados[i]
        return i, n

    def encender(self):
        print "%s: Encendiendo..." % self.name
        while self.libvirt.info()[0] != 1:
            self.libvirt.create()
            sleep(1)

    def apagar(self, timeout=3):
        print "%s: Apagando..." % self.name
        if self.libvirt.info()[0] != 1:
            return
        elif timeout < 0:
            self._force_shutdown()
            sleep(2)
            self.apagar(timeout=timeout-1)
        else:
            self.libvirt.shutdown()
            sleep(2)
            self.apagar(timeout=timeout-1)

    def _force_shutdown(self):
        if self.libvirt.info()[0] == 1:
            self.libvirt.destroy()

    def respaldar(self):
        print "%s: Iniciando respaldo" % self.name
        estado_original = self.libvirt.info()[0]

        if estado_original == 1:
            self.apagar()

        if not exists(self.ruta_respaldos):
            makedirs(self.ruta_respaldos)

        xml = open(self.ruta_respaldos+'/'+self.name+'.xml', 'w')
        xml.writelines(self.xml)
        xml.close()

        for d in self.discos():
            destino = self.ruta_respaldos+'/'+d.nombre
            d.respaldar(destino)

        if estado_original == 1:
            self.encender()

    def discos(self):
        if self._discos == []:
            self._discos = self._getDiscos()
        return self._discos

    def _getDiscos(self):
        p = parseString(self.xml)
        discos = []
        for device in p.getElementsByTagName('disk'):

            if device.getAttribute('device') != 'disk':
                continue

            d = kvmDisc(device, self.ssh)
            discos.append(d)

        return discos

    def limpiarRespaldos(self, max=2):
        """ Me quedo solo con los ultimos respaldos de cada guest """
        print "%s: Eliminando respaldos antiguos..." % self.name

        if not exists(self.ruta_respaldos_base):
            return

        for respaldo in sorted(listdir(self.ruta_respaldos_base))[:-max]:
            print '%s: Borrando respaldo %s' % (self.name, respaldo)
            borrarArbol(self.ruta_respaldos_base+'/'+respaldo)

class kvmDisc():
    def __init__(self, xml, ssh):
        self.xml = xml.toxml()
        self.ruta = xml.getElementsByTagName('source')[0].getAttribute('file')
        self.nombre = self.ruta.split('/')[-1]
        self.ssh = ssh

        sftp = self.ssh.getSftp()
        self.tamanio = sftp.lstat(self.ruta).st_size/(1024**3)  # gbs

    def __repr__(self):
        return "%s [%s GB]" % (self.ruta, self.tamanio)

    def respaldar(self, destino):
        self._copiar(destino)
        self._comprimir(destino)

    def _copiar(self, destino):
        print "Copiando %s a %s" % (self.ruta, destino)
        sftp = self.ssh.getSftp()
        sftp.get(self.ruta, destino)

    def _comprimir(self, destino):
        print "Comprimiendo %s" % destino

        try:
            f_in = open(destino, 'rb')
            f_out = gzipOpen(destino+'.gz', 'wb')
            f_out.writelines(f_in)
            f_out.close()
            f_in.close()
            remove(destino)
        except:
            pass
