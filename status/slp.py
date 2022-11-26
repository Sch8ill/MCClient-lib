#!/usr/bin/env python3

__version__ = "0.2.2"
__author__ = "Sch8ill"


import socket
import json
import time
import struct



class VarInt: # class to pack and unpack Varints
    @staticmethod
    def pack(data):
        ordinal = b''
        while data != 0:
            byte = data & 0x7F
            data >>= 7
            ordinal += struct.pack('B', byte | (0x80 if data > 0 else 0))
        return ordinal



class Packet:
    def __init__(self, id, fields=[]):
        self.id = id
        self.fields = fields
        self.varint = VarInt()


    def pack(self):
        packet = self._encode(self.id)
        for field in self.fields:
            field = self._encode(field)
            packet += field

        packet = self.varint.pack(len(packet)) + packet # add packetlength
        return packet


    def _encode(self, data):
        if type(data) == int:
            data = struct.pack("H", data)

        elif type(data) == str:
            data = data.encode("utf-8")
            data = self.varint.pack(len(data)) + data

        elif type(data) == float:
            print(data)
            data = struct.pack(">Q", int(data))
            print(data)
        return data



class SLPClient:
    def __init__(self, host="localhost", port=25565, timeout=5):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connected = False
        self.sock.settimeout(timeout)
        self.varint = VarInt()
        self.protocoll_version = self.varint.pack(4)


    def _connect(self):
        if self.connected == False: # adds ability to "implant" an alredy connected socket, usefull for scanning
            self.sock.connect((self.host, self.port))
            self.connected = True

        elif self.connected == None:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            self.connected = True


    def _send(self, packet):
        return self.sock.send(packet)


    def legacy_ping(self):
        self._connect()
        self._send(b"\xFE") # legacy status request
        res = self.sock.recv(4096)

        self.sock.close()
        self.connected = None

        res = res[4:] # remove padding and other headers
        res = res.decode("UTF-16", errors="ignore")
        data = {}
        res = res.split("§") # data is split with "§"
        data["motd"] = "".join(res[:-2])
        data["online"] = int(res[-2])
        data["max"] = int(res[-1])
        return data


    def _recv(self, extra_varint=False):
        length = self.varint.unpack(self.sock)
        packet_id = self.varint.unpack(self.sock)
        data = b""

        if extra_varint:
            if packet_id > length:
                self.varint.unpack(self.sock)

            extra_length = self.varint.unpack(self.sock)

            while len(data) < extra_length:
                data += self.sock.recv(extra_length)

        else:
            data = self.sock.recv(length)
        return data


    def _handshake(self, next_state=b"\x01"):
        fields = [
            self.protocoll_version,
            self.host,
            25565,
            next_state # next state b"\x01" for status request
        ]
        packet = Packet(b"\x00", fields)
        packet = packet.pack()
        self._send(packet)


    def _status_request(self):
        self._connect()
        self._handshake() # handshake + set connection state

        packet = Packet(b"\x00") # send status request
        packet = packet.pack()
        self._send(packet)
        res = self._recv(extra_varint=True)

        self.sock.close()
        self.connected = None

        res = res.decode("utf-8")
        res = json.loads(res)

        return res


    def get_stats(self):
        try:
            return self._status_request()

        except Exception as e:
            return e