import socket
import sys
import types
import unittest
from unittest.mock import patch
from discovery import DiscoveryAnnouncer, lan_ipv4_addresses, SERVICE_TYPE

class DiscoveryTests(unittest.TestCase):
    def test_filters_non_lan_addresses(self):
        addresses=['127.0.0.1','169.254.1.2','0.0.0.0','224.0.0.251','192.168.1.10','10.0.0.2','192.168.1.10']
        rows=[(socket.AF_INET,socket.SOCK_STREAM,6,'',(ip,0)) for ip in addresses]
        with patch('discovery.socket.getaddrinfo',return_value=rows):
            self.assertEqual(lan_ipv4_addresses(),['10.0.0.2','192.168.1.10'])
    def test_readvertises_on_network_change_without_credentials(self):
        sessions=[]
        class Connection:
            def __init__(self,**kwargs): self.options=kwargs; self.services=[]; self.closed=False; sessions.append(self)
            def register_service(self,info,**kwargs): self.services.append(info)
            def close(self): self.closed=True
        class Info:
            def __init__(self,*args,**kwargs): self.args=args; self.options=kwargs
        class Stop:
            waits=0
            def is_set(self): return self.waits>=2
            def wait(self,delay): self.waits+=1
        fake=types.SimpleNamespace(Zeroconf=Connection,ServiceInfo=Info,IPVersion=types.SimpleNamespace(V4Only=4))
        advertiser=DiscoveryAnnouncer(8000); advertiser.stop_event=Stop()
        with patch.dict(sys.modules,{'zeroconf':fake}), patch('discovery.lan_ipv4_addresses',side_effect=[['192.168.1.10'],['192.168.2.20']]):
            advertiser._run()
        self.assertEqual(len(sessions),2)
        self.assertTrue(all(s.closed for s in sessions))
        self.assertEqual(sessions[1].options['interfaces'],['192.168.2.20'])
        for session in sessions:
            info=session.services[0]
            self.assertEqual(info.args[0],SERVICE_TYPE)
            self.assertEqual(info.options['port'],8000)
            self.assertEqual(info.options['properties'],{'api':'1'})
    def test_missing_zeroconf_gives_install_instruction(self):
        with patch.dict(sys.modules,{'zeroconf':None}), patch('builtins.print') as out:
            advertiser=DiscoveryAnnouncer(8000); advertiser.start()
        self.assertIsNone(advertiser.thread)
        self.assertIn('start.bat',out.call_args.args[0])

if __name__=='__main__': unittest.main()
