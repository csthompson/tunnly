from docker.client import Client
from docker.utils import kwargs_from_env
import docker

import MySQLdb as mdb

import iso8601
import datetime

class DockerInterface:
    client = Client(**kwargs_from_env())

    def destroyContainer(self, dockerId):
        self.client.stop(dockerId)
        self.client.remove_container(dockerId)

class MysqlInterface:

    con = None

    def __init__(self, server, username, password, db):
        self.con = mdb.connect(server, username, password, db)

    def getExpiredNetworks(self, durationMinutes):

        threshholdTimestamp = datetime.datetime.now() - datetime.timedelta(minutes=durationMinutes)

        expiredNets = []

        print threshholdTimestamp.strftime('%Y-%m-%d %H:%M:%S')

        cur = self.con.cursor()
        cur.execute("SELECT DISTINCT(port_dockerId) FROM tunnly_ports WHERE port_timecreate < %s AND port_active=1", (threshholdTimestamp.strftime('%Y-%m-%d %H:%M:%S')))

        rows = cur.fetchall()

        for row in rows:
            expiredNets.append(row[0])
            cur.execute("UPDATE tunnly_ports SET port_active=0 WHERE port_dockerId = %s", (row[0]))
            self.con.commit()

        return expiredNets

dockerInst = DockerInterface()
sql = MysqlInterface('localhost', 'srv_tunnly', 'tunnlytest', 'tst_tunnly')

containers = sql.getExpiredNetworks(15)

for container in containers:
    dockerInst.destroyContainer(container)
