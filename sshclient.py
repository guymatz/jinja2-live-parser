from io import StringIO
import paramiko
import sys

class SshClient:
    "A wrapper of paramiko.SSHClient"
    TIMEOUT = 4

    def __init__(self, host, username, password, port='22', key=None, passphrase=None):
        self.username = username
        self.password = password
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if key is not None:
            key = paramiko.RSAKey.from_private_key(StringIO(key), password=passphrase)
        self.client.connect(host, port, username=username, password=password, pkey=key, timeout=self.TIMEOUT)

    def close(self):
        if self.client is not None:
            self.client.close()
            self.client = None

    def execute(self, command, sudo=False):
        feed_password = False
        if sudo and self.username != "root":
            command = "sudo -S -p '' %s" % command
            feed_password = self.password is not None and len(self.password) > 0
        stdin, stdout, stderr = self.client.exec_command(command, get_pty=True, timeout=5)
        if feed_password:
            stdin.write(self.password + "\n")
            stdin.flush()
        # Have to slice this here, otherwise the password gets included.  not sure why
        return {'out': stdout.readlines()[2:],
                'err': stderr.readlines(),
                'retval': stdout.channel.recv_exit_status()}

if __name__ == "__main__":

    args = sys.argv
    client = SshClient(host=args[1], port=22, username=args[2], password=args[3])
    try:
        ret = client.execute('cat /etc/redhat-release', sudo=True)
        print("OUT:\n%s\n" % ret['out'])
        print("ERR:\n%s\n" % ret['err'])
        print("RETVAL:\n%s\n" % ret['retval'])
        print("  ".join(ret["out"]), "  E ".join(ret["err"]), ret["retval"])
    finally:
        client.close()