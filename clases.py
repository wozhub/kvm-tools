#!/usr/bin/python

import libvirt


class kvamHost():
    def __init__(self, url="qemu:///system"):
        self.libvirt = libvirt.open(url)


    def respaldar(self):
        pass

    def _getGuests(self):
        pass


class kvmGuest():

    def apagar(self):
        pass

    def respaldar(self):
        pass

    def _getDiscos(self):
        pass

    def _shutdown(self):
        pass
