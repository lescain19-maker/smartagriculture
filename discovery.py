"""Advertise local telemetry over mDNS. No credentials are broadcast."""
import ipaddress
import socket
import threading

SERVICE_TYPE = '_smartagric._tcp.local.'


def lan_ipv4_addresses():
    """Collect active hostname IPv4 addresses, excluding loopback/link-local."""
    addresses = set()
    try:
        for result in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET, socket.SOCK_STREAM):
            address = ipaddress.ip_address(result[4][0])
            if not (address.is_loopback or address.is_link_local or address.is_unspecified or address.is_multicast):
                addresses.add(str(address))
    except OSError:
        pass
    return sorted(addresses)


class DiscoveryAnnouncer:
    def __init__(self, port):
        self.port = port
        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        try:
            import zeroconf  # noqa: F401
        except ImportError:
            print('Automatic ESP32 discovery unavailable. Run start.bat or pip install -r requirements.txt.', flush=True)
            return
        self.thread = threading.Thread(target=self._run, daemon=True, name='smartagric-discovery')
        self.thread.start()

    def _run(self):
        from zeroconf import Zeroconf, ServiceInfo, IPVersion
        current = None
        connection = None
        while not self.stop_event.is_set():
            addresses = lan_ipv4_addresses()
            if addresses != current:
                if connection:
                    connection.close()
                    connection = None
                try:
                    if addresses:
                        connection = Zeroconf(interfaces=addresses, ip_version=IPVersion.V4Only)
                        # One instance per address: the ESP32 can test each interface.
                        for address in addresses:
                            suffix = address.replace('.', '-')
                            info = ServiceInfo(
                                SERVICE_TYPE,
                                f'Smart Agric {suffix}.{SERVICE_TYPE}',
                                addresses=[socket.inet_aton(address)],
                                port=self.port,
                                server=f'smartagric-{suffix}.local.',
                                properties={'api': '1'},
                            )
                            connection.register_service(info, allow_name_change=True)
                        print('ESP32 automatic discovery active: ' + ', '.join(f'http://{a}:{self.port}' for a in addresses), flush=True)
                    else:
                        print('No LAN IPv4 address yet. Discovery will retry automatically.', flush=True)
                    current = addresses
                except Exception as exc:
                    if connection:
                        connection.close()
                        connection = None
                    current = None
                    print(f'ESP32 discovery will retry: {type(exc).__name__}. Check private-network firewall access.', flush=True)
            self.stop_event.wait(5)
        if connection:
            connection.close()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=4)
