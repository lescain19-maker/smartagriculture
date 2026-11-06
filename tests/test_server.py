import http.client
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from http.server import ThreadingHTTPServer
from server import Store, handler_for

SAMPLE = dict(soil_moisture=52.5, soil_temperature=22, air_temperature=25, humidity=63, pump=False, pump_available=True, uptime_ms=1000)

class ServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name)/'test.db')
        self.http = ThreadingHTTPServer(('127.0.0.1',0), handler_for(self.store,'test-key-for-local-tests'))
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()
    def tearDown(self):
        self.http.shutdown(); self.http.server_close(); self.thread.join()
        self.store.db.close(); self.temp.cleanup()
    def req(self, path, body=None, key='test-key-for-local-tests', origin=None):
        conn=http.client.HTTPConnection('127.0.0.1',self.http.server_port)
        headers={'X-Device-Key':key}
        if origin: headers['Origin']=origin
        conn.request('POST' if body is not None else 'GET',path,json.dumps(body) if body is not None else None,headers)
        response=conn.getresponse(); status=response.status; data=json.loads(response.read()); conn.close()
        return status,data
    def test_auth_and_origin(self):
        self.assertEqual(self.req('/api/status',key='wrong')[0],401)
        self.assertEqual(self.req('/api/status',origin='http://other.example')[0],403)
        self.assertEqual(self.req('/api/status')[1]['sample'],None)
    def test_ingestion_history_and_persistence(self):
        code,body=self.req('/api/telemetry',SAMPLE)
        self.assertEqual(code,200)
        self.assertEqual(body['sample']['soil_moisture'],52.5)
        self.assertTrue(self.req('/api/status')[1]['online'])
        self.assertEqual(len(self.req('/api/history?minutes=60')[1]['samples']),1)
        reopened=Store(Path(self.temp.name)/'test.db')
        self.assertEqual(reopened.latest()['air_temperature'],25)
        reopened.db.close()
    def test_invalid_packets_do_not_replace_valid_values(self):
        self.req('/api/telemetry',SAMPLE)
        for field,value in [('humidity',101),('soil_temperature',-127),('soil_moisture',True),('air_temperature',None),('pump',1)]:
            with self.subTest(field=field):
                self.assertEqual(self.req('/api/telemetry',{**SAMPLE,field:value})[0],400)
        self.assertEqual(len(self.store.history(60)),1)
    def test_lora_packet_without_soil_temperature(self):
        packet = {**SAMPLE, 'soil_temperature': None}
        self.assertEqual(self.req('/api/telemetry',packet)[0],200)
        latest = self.req('/api/status')[1]['sample']
        self.assertIsNone(latest['soil_temperature'])
        self.assertEqual(latest['air_temperature'],25)
        del packet['soil_temperature']
        self.assertEqual(self.req('/api/telemetry',packet)[0],200)
        self.assertEqual(self.req('/api/telemetry',{**packet,'humidity':None})[0],400)

    def test_pump_requires_fresh_available_device(self):
        self.assertEqual(self.req('/api/pump',{'pump':True})[0],409)
        self.req('/api/telemetry',{**SAMPLE,'pump_available':False})
        self.assertEqual(self.req('/api/pump',{'pump':True})[0],409)
        self.req('/api/telemetry',SAMPLE)
        self.assertEqual(self.req('/api/pump',{'pump':True})[0],200)
        self.assertTrue(self.req('/api/command')[1]['pump'])
        with self.store.lock:
            row=self.store.db.execute('SELECT id,payload FROM readings ORDER BY id DESC LIMIT 1').fetchone()
            sample=json.loads(row[1]); sample['time']=int(time.time()*1000)-20000
            self.store.db.execute('UPDATE readings SET payload=? WHERE id=?',(json.dumps(sample),row[0])); self.store.db.commit()
        self.assertFalse(self.req('/api/status')[1]['online'])
        self.assertFalse(self.req('/api/command')[1]['pump'])
        self.assertEqual(self.req('/api/pump',{'pump':True})[0],409)
        self.assertEqual(self.req('/api/pump',{'pump':False})[0],200)

if __name__=='__main__': unittest.main()
