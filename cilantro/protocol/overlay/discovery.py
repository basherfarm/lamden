import zmq, zmq.asyncio, asyncio, traceback
from os import getenv as env
from cilantro.constants.overlay_network import *
from cilantro.constants.ports import DISCOVERY_PORT
from cilantro.protocol.overlay.ip import *
from cilantro.protocol.overlay.auth import Auth
from cilantro.logger import get_logger
from cilantro.storage.vkbook import VKBook


class Discovery:
    log = get_logger('Discovery')
    host_ip = HOST_IP
    port = DISCOVERY_PORT
    url = 'tcp://*:{}'.format(port)
    pepper = PEPPER.encode()
    discovered_nodes = {}
    connections = {}
    is_setup = False
    is_listen_ready = False

    @classmethod
    def setup(cls, ctx=None):
        if not cls.is_setup:
            cls.is_setup = True
            cls.ctx = ctx or zmq.asyncio.Context()
            cls.sock = cls.ctx.socket(zmq.ROUTER)
            cls.is_connected = False
            if VKBook.is_node_type('masternode', Auth.vk):
                # cls.discovered_nodes[Auth.vk] = cls.host_ip
                cls.is_master_node = True
                cls.is_listen_ready = True

    @classmethod
    async def listen(cls):
        cls.sock.setsockopt(zmq.IDENTITY, cls.host_ip.encode())
        cls.sock.bind(cls.url)
        cls.log.info('Listening to other nodes on {}'.format(cls.url))
        if cls.is_listen_ready:
            pass
            # await asyncio.sleep(0)
        while True:
            try:
                msg = await cls.sock.recv_multipart()
                cls.log.spam("Got msg over discovery socket: {}".format(msg))
                ip, pepper = msg[:2]

                if pepper != cls.pepper:
                    cls.log.warning("Node with ip {} tried to connect using incorrect pepper {}!".format(ip, pepper))
                    continue

                if len(msg) == 2:
                    cls.reply(ip)
                elif len(msg) == 3:
                    vk = msg[-1]
                    cls.discovered_nodes[vk.decode()] = ip.decode()
                    cls.is_listen_ready = True

            except Exception as e:
                cls.log.error(traceback.format_exc())

    @classmethod
    async def discover_nodes(cls, start_ip):
        is_masternode = VKBook.is_node_type('masternode', Auth.vk)
        try_count = 0

        cls.log.spam('We have the following bootnodes: {}'.format(VKBook.bootnodes))

        while True:
            if len(VKBook.bootnodes) > 0: # TODO refine logic post-anarchy-net
                cls.log.info('Connecting to boot nodes: {}'.format(VKBook.bootnodes))
                cls.connect(VKBook.bootnodes)
            else:
                cls.log.info('Connecting to this ip-range: {}'.format(start_ip))
                cls.connect(get_ip_range(start_ip))
            try_count += 1
            if (is_masternode and len(VKBook.get_masternodes()) == 1) or \
                    (len(cls.discovered_nodes) == 0 and is_masternode and cls.is_connected):
                cls.log.important('Bootstrapping as the only masternode. (num_discovered={})'
                                  .format(len(cls.discovered_nodes)))
                cls.discovered_nodes[Auth.vk] = cls.host_ip
                return True
            elif len(cls.discovered_nodes) >= MIN_BOOTSTRAP_NODES:
                cls.log.info('Found {} nodes to bootstrap: {}'.format(
                    len(cls.discovered_nodes), cls.discovered_nodes
                ))
                return True
            elif try_count >= DISCOVERY_RETRIES:
                cls.log.info('Did not find enough nodes after {} tries ({}/{}).'.format(
                    try_count,
                    len(cls.discovered_nodes),
                    MIN_BOOTSTRAP_NODES
                ))
                return False

            await asyncio.sleep(DISCOVERY_TIMEOUT)

    # raghu these class methods are not thread-safe. Not sure why we want them to be class methods rather than instance methods
#    @classmethod
#    async def discover_nodes(cls, start_ip):
#        try_count = 0
#        cls.log.info('Connecting to this ip-range: {}'.format(start_ip))
#        ips = get_ip_range(start_ip)
#        while try_count < DISCOVERY_RETRIES:
#            try_count += 1
#            for ip in ips:
#                if ip in cls.connections:
#                    continue
#                url = 'tcp://{}:{}'.format(ip, cls.port)
#                cls.sock.connect(url)
#                cls.connections[ip] = url
#                cls.request(ip.encode())
#                if (len(cls.discovered_nodes) == 1 and Auth.vk in VKBook.get_masternodes()) \
#                    and try_count >= 2:
#                    cls.log.important('Bootstrapping as the only masternode.'.format(
#                        len(cls.discovered_nodes)
#                    ))
#                    return True
#                elif len(cls.discovered_nodes) >= MIN_BOOTSTRAP_NODES:
#                    cls.log.info('Found {} nodes to bootstrap.'.format(
#                        len(cls.discovered_nodes)
#                    ))
#                    return True
#            await asyncio.sleep(DISCOVERY_TIMEOUT)
#        assert try_count >= DISCOVERY_RETRIES:
#        cls.log.info('Did not find enough nodes after {} tries ({}/{}).'.format(
#            try_count,
#            len(cls.discovered_nodes),
#            MIN_BOOTSTRAP_NODES
#        ))
#        return False

    @classmethod
    def request(cls, ip):
        cls.sock.send_multipart([ip, cls.pepper])

    @classmethod
    def reply(cls, ip):
        if cls.is_listen_ready and ip != cls.host_ip:
            cls.sock.send_multipart([ip, cls.pepper, Auth.vk.encode()])
            cls.is_connected = True

    @classmethod
    def connect(cls, ips):
        for ip in ips:
            if ip == cls.host_ip:
                continue
            url = 'tcp://{}:{}'.format(ip, cls.port)
            cls.log.spam("Attempting to connect to IP {}".format(url))
            cls.sock.connect(url)
            cls.connections[ip] = url
            cls.request(ip.encode())
