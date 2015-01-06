Tunnly
======

###tl;dr
Dynamic network provisioning and time-based network destructor based on OpenVPN

###Why?
Why go through all the trouble with creating an account when you need some computers/machines linked for a small amount of time? Tunnly allows you to generate a network on the fly, and protect/anonymize it with a 4 digit passcode and simple shortcode. Think imgur or bit.ly, but for networks. Networks expire after 15 minutes, just enough time to get those few files transfered, or to setup some simple infrastructure without going through all the hastle of setting up a user account.

### Server requirements:

- Python 2.76
- Docker
- MySQL

Python Modules:
- Flask
- MySQLdb 
- docker-py
