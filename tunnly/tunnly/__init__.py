from docker.client import Client
from docker.utils import kwargs_from_env
import docker

from flask import Flask
from flask import Response
from flask import render_template
from flask import redirect
from flask import url_for
from flask import request
from flask import flash

import MySQLdb as mdb

import random
import os
import tarfile, io
import time
import subprocess
import shlex
import socket

from Crypto import Random
from Crypto.Cipher import AES
import base64




class DockerInterface:
    client = Client(base_url='unix://var/run/docker.sock')

    def __createNetContainer(self, udp, tcp):
        print "STRING" + str(udp) + str(tcp)

        config = self.client.create_host_config(
            privileged= True, 
            port_bindings={
                '1194/udp': udp, 
                443: tcp,
            }
        )

        container = self.client.create_container(
            image='csthompson/dockvpn',
            detach= 1,
            ports=[(1194, 'udp'), 443],
            host_config= config
        )
        print "Container created"
        return container

    def __startNetContainer(self, container):
        print str(container.get('Id'))
        response = self.client.start(
            container=container.get('Id'),
        )

    def newNetwork(self, udp, tcp):
        print "UDP STRING"
        print str(udp)
        container = self.__createNetContainer(udp, tcp)
        response = self.__startNetContainer(container)
        return container

    def killNetwork(sef, dockerId):
        self.client.stop(dockerId)
        self.client.remove_container(dockerId)

    def retrieveConfig(self, dockerId, dest):
        reply = None
        while True:
            try:
                reply = self.client.copy(dockerId, "/etc/openvpn/client.ovpn")
                break
            except docker.errors.APIError:
                continue
        size = 0
        file = None

        #Wait until the file is created to write to the host machine
        while size == 0:
            reply = self.client.copy(dockerId, "/etc/openvpn/client.ovpn")
            filelike = io.BytesIO(reply.read())
            tar = tarfile.open(fileobj = filelike)
            file = tar.extractfile("client.ovpn")
            size = tar.getmember("client.ovpn").size
            time.sleep(1)
        with open(dest, 'wb') as f:
            f.write(file.read())

class MysqlInterface:

    con = None

    def __init__(self, server, username, password, db):
        self.con = mdb.connect(server, username, password, db)

    def createNewPortRecord(self, dockerId, tunnlyId, port, proto):
        cur = self.con.cursor()
        cur.execute("INSERT INTO tunnly_ports(port_dockerId, port_number, tunnly_code, port_proto) VALUES(%s, %s, %s, %s)",
            (dockerId, port, tunnlyId, proto))
        self.con.commit()

    def checkIfPortExists(self, port):
        cur = self.con.cursor()
        cur.execute("SELECT * FROM tunnly_ports WHERE port_number = %s AND port_active=1", (port))
        if cur.rowcount < 1:
            return 0
        else:
            return 1

class AESCipher:

    def __init__( self, key ):
        self.key = key

    def encrypt( self, raw ):
        BS = 16
        pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)
        raw = pad(raw)
        iv = Random.new().read( AES.block_size )
        cipher = AES.new( self.key, AES.MODE_CBC, iv,  segment_size=AES.block_size*8 )
        return base64.b64encode( iv + cipher.encrypt( raw ) )

    def decrypt( self, enc ):
        BS = 16
        unpad = lambda s : s[:-ord(s[len(s)-1:])]
        enc = base64.b64decode(enc)
        iv = enc[:16]
        cipher = AES.new(self.key, AES.MODE_CBC, iv, segment_size=AES.block_size*8 )
        return unpad(cipher.decrypt( enc[16:] ))

class HostInterface:

    def encryptConfig(self, filename, key):
        cipher = AESCipher(key)
        data = ""
        with open (filename, "r") as myfile:
            data=myfile.read()
        cipherText = cipher.encrypt(data)
        with open(filename, 'w') as f:
            f.write(cipherText)

    def modifyConfig(self, udp, tcp, dockerId):
        #Get the current host's ip address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 0))  # connecting to a UDP address doesn't send packets
        local_ip_address = s.getsockname()[0]

        udpChange = "sed -i 's/^remote " + str(local_ip_address) + " 1194 udp*/remote " + str(local_ip_address) + " " +  str(udp) + " udp/' /tmp/clientConfigs/" + dockerId + ".ovpn"
        tcpChange = "sed -i 's/^remote " + str(local_ip_address) + " 443 tcp-client*/remote " + str(local_ip_address) + " " +  str(tcp) + " tcp-client/' /tmp/clientConfigs/" + dockerId + ".ovpn"
        
        err = subprocess.call(shlex.split(udpChange))
        print "Error for udp change ", err
        err = subprocess.call(shlex.split(tcpChange))
        print "Error for tcp change ", err


def createNewNetwork(passcode):


    sql = MysqlInterface('localhost', 'srv_tunnly', 'tunnlytest', 'tst_tunnly')
    dockerInst = DockerInterface()

    random.seed()
    udp = random.randint(1024, 49151)
    tcp = random.randint(1024, 49151)


    #Make sure each port is unique
    while udp == tcp or sql.checkIfPortExists(udp) or sql.checkIfPortExists(tcp):
        udp = random.randint(1024, 49151)
        tcp = random.randint(1024, 49151)

    #Create the new network (OpenVPN docker container)
    container = dockerInst.newNetwork(udp, tcp)
    dockerId = container.get('Id')

    sql.createNewPortRecord(dockerId[:12], dockerId[:12], udp, 'udp')
    sql.createNewPortRecord(dockerId[:12], dockerId[:12], tcp, 'tcp')

    #Attempt to retrieve the config file until it can be retrieved
    dockerInst.retrieveConfig(dockerId, "/tmp/clientConfigs/" + dockerId[:12] + ".ovpn")

    hostInt = HostInterface()

    hostInt.modifyConfig(udp, tcp, dockerId[:12])

    hostInt.encryptConfig("/tmp/clientConfigs/" + dockerId[:12] + ".ovpn", passcode.ljust(32, '0'))

    return dockerId[:12]

app = Flask(__name__)
app.secret_key = 'xxxjjjtesttunnly1234567890'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/network/confirm')
def sendConfirmation():
    return render_template('confirmation.html')

@app.route('/network/new', methods=['POST'])
def newNetwork():
    assert request.method == 'POST'
    if request.method == 'POST':
        pass_code = request.form['passcode'],
        if len(str(pass_code[0])) < 4:
            flash("Passcode must be 4 characters!")
            return redirect(url_for('index'))
        print str(pass_code[0])
    tunnlyCode = createNewNetwork(str(pass_code[0]))
    flash(tunnlyCode)
    return redirect(url_for('sendConfirmation'))

@app.route('/network/config/<tunnly_id>')
def getConfig(tunnly_id):
    filename = "/tmp/clientConfigs/" + tunnly_id + ".ovpn"
    data = ""
    with open (filename, "r") as myfile:
        data=myfile.read()
    resp = Response(response=data,
        status=200,
        mimetype="application/x-openvpn-profile")
    return resp

if __name__ == '__main__':
    app.debug = True
    app.run()
