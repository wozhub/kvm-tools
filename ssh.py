
from paramiko import Transport, SFTPClient, SSHClient, AutoAddPolicy, RSAKey
from os.path import expanduser


class ssh_wrapper():

    def __init__(self, host, port, user, pw):
        self.transport = Transport((host, port))
        self._datos = {'host': host, 'port': port, 'user': user, 'pw': pw}
        self.rsa_key = None

        self.setPrivateKey(expanduser('~/.ssh/id_rsa'))
        self.conectar()

    def conectar(self):
        if self.rsa_key is None:
            self.transport.connect(username=self._datos['user'],
                                   password=self._datos['pw'])
        else:
            self.transport.connect(username=self._datos['user'],
                                   pkey=self.rsa_key)
        self.transport.set_keepalive(60)

    def setPrivateKey(self, path):
        self.rsa_key = RSAKey.from_private_key_file(path)

    def getCiphers(self):
        return self.transport.get_security_options()._get_ciphers()

    def setCipher(self, cipher):
        self.transport = Transport((self._datos['host'],
                                    self._datos['port']))

        self.transport.get_security_options().ciphers = [cipher, ]

        self.transport.connect(username=self._datos['user'],
                               password=self._datos['pw'])

        self.transport.set_keepalive(60)

    def getSftp(self):
        return SFTPClient.from_transport(self.transport)

    def getSsh(self):
        self.ssh = SSHClient()
        self.ssh.set_missing_host_key_policy(AutoAddPolicy())
