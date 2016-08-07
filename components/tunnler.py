#Docker Dependencies
from docker.client import Client
from docker.utils import kwargs_from_env
import docker

#Built-in Python dependencies
import random
import os
import tarfile, io
import time
import subprocess
import shlex
import socket
import sqlite3

#Cryptography dependencies
from Crypto import Random
from Crypto.Cipher import AES
import base64


class DockerInterface:
    client = Client(base_url='unix://var/run/docker.sock')

    #Helper function to create the new OpenVPN container
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

    #Helper function to start the new OpenVPN container
    def __startNetContainer(self, container):
        print str(container.get('Id'))
        response = self.client.start(
            container=container.get('Id'),
        )

    #Create a new OpenVPN container with a specifc UDP and TCP port opened
    def newNetwork(self, udp, tcp):
        print "UDP STRING"
        print str(udp)
        container = self.__createNetContainer(udp, tcp)
        response = self.__startNetContainer(container)
        return container

    #Destroy the network (used when the network expires)
    def killNetwork(sef, dockerId):
        self.client.stop(dockerId)
        self.client.remove_container(dockerId)

    #Retrieve the "client.ovpn" file from the OpenVPN container. Distributed to client for conection.
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


#Routing table between Docker interface and internal OpenVPN containers
class RouteTableInterface:

    db = 'routes.db'

    #Create the routes database and the routes table if it does not exist
    def __init__(self):
        self.con = sqlite3.connect(self.db)
        self.con.execute('''CREATE TABLE IF NOT EXISTS routes
            (route_id       INTEGER     PRIMARY KEY     AUTOINCREMENT   ,
            docker_id       CHAR(25)                                NOT NULL,
            tunnly_id       CHAR(25)                                NOT NULL,
            tcp_port        INTEGER                                     NOT NULL,
            udp_port        INTEGER                                    NOT NULL,
            expire_time     INTEGER                                     NOT NULL,
            route_active    INTEGER                                     NOT NULL);''')


    #Create a new route in the routing table
    def createNewRouteRecord(self, dockerId, tunnlyId, tcpPort, udpPort, expire_time):
        con = sqlite3.connect(self.db)
        con.execute("INSERT INTO routes(docker_id, tunnly_id, tcp_port, udp_port, expire_time, route_active) VALUES(?, ?, ?, ?, ?, 1)",
            (dockerId, tunnlyId, tcpPort, udpPort, expireTime))
        con.commit()
        con.close()

    #Check if a port number (TCP or UDP in type) has been used
    def checkIfPortExists(self, portType, port):
        con = sqlite3.connect(self.db)
        if portType == 'tcp':
            con.execute("SELECT * FROM routes WHERE tcp_port = ? AND route_active=1", (port,))
        else:
            con.execute("SELECT * FROM routes WHERE udp_port = ? AND route_active=1", (port,))
        row = con.fetchone()
        if row is None:
            return 0
        else:
            return 1

        con.close()

    #Check if a Tunnly shortcode has been used
    def checkIfTunnlyCodeExists(self, code):
        con = sqlite3.connect(self.db)
        con.execute("SELECT * FROM routes WHERE tunnly_id = ? AND route_active=1", (code))
        row = con.fetchone()
        if row is None:
            return 0
        else:
            return 1

        con.close()

#Class used to help with encryption of the OpenVPN configuration files
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

#Class used to help with host related function, such as configuration file modifications and file encryption
class HostInterface:

    #Encrypt the OpenVPN configuration file once it has been copied over
    def encryptConfig(self, filename, key):
        cipher = AESCipher(key)
        data = ""
        with open (filename, "r") as myfile:
            data=myfile.read()
        cipherText = cipher.encrypt(data)
        with open(filename, 'w') as f:
            f.write(cipherText)

    #Modify the OpenVPN configuration file to reflect the host's IP address and to forward to the correct OpenVPN Docker container
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

class Tunnler:
    #Create a new Tunnly connection
    def createNewNetwork(self, passcode, expiration):

        #Possibly use SQLite in future use to make Tunnly Worker more portable
        sql = RouteTableInterface()
        dockerInst = DockerInterface()

        #Pick random UDP and TCP port numbers
        random.seed()
        udp = random.randint(1024, 49151)
        tcp = random.randint(1024, 49151)


        #Make sure each port is unique by checking it against the database
        while udp == tcp or sql.checkIfPortExists('udp', udp) or sql.checkIfPortExists('tcp', tcp):
            udp = random.randint(1024, 49151)
            tcp = random.randint(1024, 49151)

        #Create the new network (OpenVPN docker container)
        container = dockerInst.newNetwork(udp, tcp)
        #Get the ID of the OpenVPN docker container
        dockerId = container.get('Id')

        #Use the sql interface to create a new UDP port record
        sql.createNewPortRecord(dockerId[:12], dockerId[:12], udp, 'udp')
        #Use the sql interface to create a new TCP port record
        sql.createNewPortRecord(dockerId[:12], dockerId[:12], tcp, 'tcp')

        #Attempt to retrieve the config file until it can be retrieved (may take a while while Diffie Hellman parameters are generated on Docker container)
        dockerInst.retrieveConfig(dockerId, "/tmp/clientConfigs/" + dockerId[:12] + ".ovpn")

        #Create an instance of the class used to manage the Docker Host functions
        hostInt = HostInterface()

        #Uses sed to modify the ovpn configuration files that are copied over from the docker container
        hostInt.modifyConfig(udp, tcp, dockerId[:12])

        #Encrypt the configuration file using the passcode from the user input
        hostInt.encryptConfig("/tmp/clientConfigs/" + dockerId[:12] + ".ovpn", passcode.ljust(32, '0'))

        #return the docker container ID once the network container is up
        return dockerId[:12]


tun = Tunnler()
tun.createNewNetwork("1123", "test")