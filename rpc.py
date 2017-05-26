import io
import json
import random
import re
import socket
import ssl


class MRPCError(Exception):
    pass


class SocketMaker(object):

    def __init__(self, cert_path, password):
        self.ctx = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE
        self.ctx.load_cert_chain(cert_path, password=password)

    def get_socket(self):
        s = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        return self.ctx.wrap_socket(s)


class MRPCSession(object):

    eol = '\r\n'
    response_count = {True: "multiple", False: "single"}
    schema_version = "17"
    proto_pat = re.compile("^.*MRPC/2 (?P<h_size>\d+) (?P<b_size>\d+)\r\n")

    def __init__(self, socket_maker, address, mak, port=1413, debug=False):
        self.sm = socket_maker
        self.mak = mak
        self.address = address
        self.port = port
        self.socket = None
        self.session_id = random.randint(0, 2**32 - 1)
        self.rpc_id = 0
        self.body_id = ""
        self.debug = debug

    def connect(self):
        self.socket = self.sm.get_socket()
        self.socket.connect((self.address, self.port))
        if not self.do_auth():
            self.socket.shutdown()
            self.socket.close()
            self.socket = None
            raise MRPCError("Auth Failure")
        self.send_request("bodyConfigSearch", {"bodyId": "-"})
        h, r = self.get_response()
        try:
            self.body_id = r['bodyConfig'][0]['bodyId']
        except KeyError:
            self.body_id = "-"

    def close(self):
        if self.socket is not None:
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
            self.socket = None

    def send_request(self, req_type, payload_json, multiple_responses=False):
        body_id = ""
        if "bodyId" in payload_json:
            body_id = payload_json["bodyId"]

        header_tuples = (
            ("Type", "request"),
            ("RpcId", "{:d}".format(self.rpc_id)),
            ("SchemaVersion", "{}".format(self.schema_version)),
            ("Content-Type", "application/json"),
            ("RequestType", req_type),
            ("ResponseCount", self.response_count[multiple_responses]),
            ("BodyId", body_id),
            ("X-ApplicationName", "Quicksilver"),
            ("X-ApplicationVersion", "1.2"),
            ("X-ApplicationSessionId", "0x{:x}".format(self.session_id)),
        )

        headers = self.eol.join(["{}: {}".format(k, v) for k, v in header_tuples]) + self.eol

        payload_json['type'] = req_type
        payload = json.dumps(payload_json)
        preamble = "MRPC/2 {:d} {:d}".format(len(headers) + 2, len(payload))
        request = preamble + self.eol + headers + self.eol + payload + "\n"
        self.rpc_id += 1

        self.socket.sendall(request.encode('ascii'))

    @staticmethod
    def parse_headers(buffer):
        return dict([line.split(': ', 1) for line in buffer.split('\r\n') if len(line) > 0])

    def get_response(self):
        buffer = io.BytesIO()
        buffer.write(self.socket.recv())
        while b"\n" not in buffer.getvalue():
            buffer.write(self.socket.recv())
        buf_val = buffer.getvalue().decode()
        m = self.proto_pat.search(buf_val)
        h_size = int(m.groupdict()['h_size'])
        b_size = int(m.groupdict()['b_size'])
        h_start = m.span()[-1]
        if self.debug:
            print("RPC Response (Offset: {:d}, H Size: {:d}, B Size: {:d})".format(h_start, h_size, b_size))
            print("RPC Response (Bytes Loaded: {:d})".format(buffer.tell() - h_start))
        while buffer.tell() - h_start < h_size + b_size:
            buffer.write(self.socket.recv())
            if self.debug:
                print("RPC Response (Bytes Loaded: {:d})".format(buffer.tell() - h_start))
        buf_val = buffer.getvalue().decode()
        headers = self.parse_headers(buf_val[h_start:h_start+h_size])
        response_json = json.loads(buf_val[h_start+h_size:])
        return headers, response_json

    def do_auth(self):
        payload_json = {"credential": {"type": "makCredential", "key": self.mak}}
        self.send_request("bodyAuthenticate", payload_json)
        h, r = self.get_response()
        try:
            return r["status"]
        except KeyError:
            pass
        raise MRPCError("Auth Error, No Auth Status Response.")

    @staticmethod
    def get_date_string(date_time):
        return date_time.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def new_session(cert_path, password, address, mak, port=1413, debug=False):
        sm = SocketMaker(cert_path=cert_path, password=password)
        return MRPCSession(socket_maker=sm,
                           address=address,
                           mak=mak,
                           port=port,
                           debug=debug)
