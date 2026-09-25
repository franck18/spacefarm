"""Tests du serveur SpaceFarm et de sa base. Bibliothèque standard uniquement.

    cd ~/spacefarm && python3 -m unittest discover -s backend -v

Chaque test travaille sur une base temporaire : la base de production
(/var/lib/spacefarm/spacefarm.db) n'est jamais touchée.
"""
from functools import partial
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import db
from routes import Handler, snapshot


def make_config(path, **overrides):
    config = {'db': str(path), 'token': '', 'stale': 120, 'retention': 7,
              'history_hours': 6, 'reservoir': 10.0}
    config.update(overrides)
    return config


class TemporaryDatabase(unittest.TestCase):
    def setUp(self):
        self._folder = tempfile.TemporaryDirectory()
        self.db_path = Path(self._folder.name) / 'test.db'
        db.initialise(self.db_path)
        self.config = make_config(self.db_path)

    def tearDown(self):
        self._folder.cleanup()

    def ingest(self, sensor='serre-01', **readings):
        parsed = db.parse_payload({'sensor': sensor, 'readings': readings})
        return db.store_readings(self.db_path, *parsed)


class EmptyDatabaseTests(TemporaryDatabase):
    def test_no_sensor_yields_no_invented_measurement(self):
        """Sans capteur, l'API ne doit jamais présenter une valeur plausible."""
        state = snapshot(self.config)
        self.assertEqual(state['mode'], 'unconfigured')
        self.assertEqual(state['history'], [])
        self.assertIsNone(state['reservoirLiters'])
        self.assertIsNone(state['pump'])
        self.assertFalse(state['system']['controlsAvailable'])
        for reading in state['measurements'].values():
            self.assertIsNone(reading['value'])
            self.assertEqual(reading['quality'], 'error')


class IngestionTests(TemporaryDatabase):
    def test_small_reservoir_keeps_milliliter_precision(self):
        self.ingest(water_raw=102.5)
        state = snapshot(make_config(self.db_path, reservoir=0.05))
        self.assertEqual(state['reservoirCapacity'], 0.05)
        self.assertEqual(state['reservoirLiters'], 0.0072)

    def test_led_state_enables_remote_lighting_control(self):
        self.ingest(lighting=1)
        state = snapshot(self.config)
        self.assertIs(state['lighting'], True)
        self.assertTrue(state['system']['controlsAvailable'])
        self.assertIsNone(state['pump'])

    def test_reading_reaches_the_dashboard(self):
        self.ingest(temperature=23.4, humidity=61, light_raw=205.3, water_raw=102.5)
        state = snapshot(self.config)
        self.assertEqual(state['mode'], 'automatic')
        self.assertEqual(state['measurements']['temperature']['value'], 23.4)
        self.assertEqual(state['measurements']['temperature']['quality'], 'ok')
        self.assertEqual(state['reservoirLiters'], 1.43)
        self.assertEqual(len(state['history']), 1)
        self.assertEqual(state['history'][0]['temperature'], 23.4)

    def test_null_means_broken_sensor_not_zero(self):
        """Un capteur en panne envoie null ; il ne doit pas devenir 0."""
        self.ingest(temperature=None)
        measurement = snapshot(self.config)['measurements']['temperature']
        self.assertIsNone(measurement['value'])
        self.assertEqual(measurement['quality'], 'error')

    def test_implausible_value_is_flagged_not_trusted(self):
        self.ingest(temperature=300)
        measurement = snapshot(self.config)['measurements']['temperature']
        self.assertEqual(measurement['quality'], 'error')
        self.assertIsNone(measurement['value'])

    def test_dht11_physical_limits_are_enforced(self):
        self.ingest(temperature=-1, humidity=10)
        state = snapshot(self.config)
        self.assertIsNone(state['measurements']['temperature']['value'])
        self.assertIsNone(state['measurements']['humidity']['value'])

    def test_stale_reading_is_downgraded(self):
        """Une mesure périmée n'est pas une mesure valide."""
        self.ingest(temperature=23.4)
        fresh = db.latest_measurements(self.db_path, stale_after_s=120)
        self.assertEqual(fresh['temperature']['quality'], 'ok')
        expired = db.latest_measurements(self.db_path, stale_after_s=0)
        self.assertEqual(expired['temperature']['quality'], 'error')
        self.assertIsNone(expired['temperature']['value'])
        self.assertEqual(db.history(self.db_path)[0]['temperature'], 23.4)

    def test_energy_metrics_coexist_with_greenhouse(self):
        """Le pilier Énergie entre dans le même schéma, sans migration."""
        db.store_readings(self.db_path, *db.parse_payload(
            {'sensor': 'energie-01', 'pillar': 'energytech',
             'readings': {'power': 430, 'battery': 86}}))
        self.ingest(temperature=23.4)
        metrics = {m['metric']: m for m in db.all_metrics(self.db_path)}
        self.assertEqual(metrics['power']['pillar'], 'energytech')
        self.assertEqual(metrics['temperature']['pillar'], 'foodtech')

    def test_sensor_registry_tracks_arrival(self):
        self.ingest(temperature=23.4)
        registry = db.sensors(self.db_path)
        self.assertEqual(len(registry), 1)
        self.assertEqual(registry[0]['sensor'], 'serre-01')
        self.assertTrue(registry[0]['online'])


class ThresholdTests(TemporaryDatabase):
    def test_alert_fires_once_on_crossing(self):
        """L'alerte se déclenche au franchissement, pas à chaque relevé."""
        self.assertEqual(self.ingest(temperature=23.0), [])
        first = self.ingest(temperature=34.0)
        self.assertEqual(len(first), 1)
        self.assertIn('hors plage', first[0])
        self.assertEqual(self.ingest(temperature=35.0), [])   # toujours hors plage
        recovery = self.ingest(temperature=23.0)
        self.assertEqual(len(recovery), 1)
        self.assertIn('revenu dans la plage', recovery[0])


class ValidationTests(TemporaryDatabase):
    def test_payloads_that_must_be_refused(self):
        refused = [
            {'readings': {'temperature': 20}},                    # sensor manquant
            {'sensor': 'x', 'readings': {}},                      # aucune mesure
            {'sensor': 'x', 'readings': {'DROP TABLE': 1}},       # métrique invalide
            {'sensor': 'x', 'readings': {'temperature': 'abc'}},  # valeur texte
            {'sensor': 'x', 'readings': {'temperature': True}},   # booléen
            {'sensor': '../../etc', 'readings': {'t': 1}},        # identifiant douteux
            {'sensor': 'x', 'readings': {'t': float('inf')}},     # non fini
            'pas un objet',
        ]
        for payload in refused:
            with self.subTest(payload=payload):
                with self.assertRaises(db.IngestError):
                    db.parse_payload(payload)

    def test_metric_name_cannot_be_injected(self):
        """Les noms de métriques entrent dans une requête SQL : ils sont filtrés."""
        self.ingest(temperature=23.4)
        rows = db.history(self.db_path, metrics=['temperature; DROP TABLE readings'])
        self.assertEqual(rows, [])
        self.assertEqual(db.stats(self.db_path)['readings'], 1)

    def test_absurd_timestamp_is_realigned(self):
        """Une carte sans horloge envoie 0 : le Pi recale sur son heure."""
        _, _, _, _, observed_at, _ = db.parse_payload(
            {'sensor': 'x', 'observedAt': 0, 'readings': {'temperature': 20}})
        self.assertGreater(observed_at, db.now_ms() - 5000)


class RetentionTests(TemporaryDatabase):
    def test_purge_removes_only_old_rows(self):
        old = db.now_ms() - 10 * 86_400_000
        db.store_readings(self.db_path, 'serre-01', 'foodtech', None, None, old,
                          [{'metric': 'temperature', 'value': 20.0, 'unit': '°C', 'quality': 'ok'}])
        self.ingest(temperature=23.4)
        self.assertEqual(db.stats(self.db_path)['readings'], 2)
        self.assertEqual(db.purge(self.db_path, retention_days=7), 1)
        self.assertEqual(db.stats(self.db_path)['readings'], 1)


class HttpTests(TemporaryDatabase):
    def setUp(self):
        super().setUp()
        self.static = Path(self._folder.name) / 'dist'
        self.static.mkdir()
        (self.static / 'index.html').write_text('<h1>SpaceFarm</h1>')
        (Path(self._folder.name) / 'secret.txt').write_text('ne doit jamais etre servi')
        self.server = ThreadingHTTPServer(
            ('127.0.0.1', 0), partial(Handler, static_dir=self.static, config=self.config))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = 'http://127.0.0.1:{}'.format(self.server.server_port)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        super().tearDown()

    def post(self, path, payload, headers=None):
        request = Request(self.base + path, data=json.dumps(payload).encode('utf-8'),
                          method='POST', headers=headers or {})
        request.add_header('Content-Type', 'application/json')
        return urlopen(request)

    def test_serves_dashboard_and_state(self):
        with urlopen(self.base + '/api/state') as response:
            self.assertEqual(json.load(response)['source'], 'live')
        with urlopen(self.base + '/') as response:
            self.assertIn(b'SpaceFarm', response.read())

    def test_ingest_round_trip(self):
        with self.post('/api/ingest', {'sensor': 'serre-01',
                                       'readings': {'temperature': 23.4}}) as response:
            self.assertEqual(response.status, 201)
            self.assertEqual(json.load(response)['stored'], 1)
        with urlopen(self.base + '/api/state') as response:
            self.assertEqual(json.load(response)['measurements']['temperature']['value'], 23.4)

    def test_pi_automates_led_and_manual_mode_over_ingest(self):
        sensor = 'spacefarm-yun'
        with self.post('/api/ingest', {'sensor': sensor,
                                       'readings': {'light_raw': 714, 'lighting': 0}}) as response:
            raw_response = response.read()
            self.assertIn(b'"command":"lighting 1 ', raw_response)
            first = json.loads(raw_response)
        self.assertRegex(first['command'], r'^lighting 1 \d+$')
        first_id = int(first['command'].split()[-1])
        with self.post('/api/ingest', {'sensor': sensor, 'ack': first_id,
                                       'readings': {'light_raw': 950, 'lighting': 1}}) as response:
            self.assertEqual(json.load(response)['command'], '')
        with urlopen(self.base + '/api/state') as response:
            state = json.load(response)
        self.assertIs(state['lighting'], True)
        self.assertTrue(state['system']['controlsAvailable'])
        self.assertEqual(state['mode'], 'automatic')

        with self.post('/api/mode', {'mode': 'manual'}) as response:
            self.assertEqual(json.load(response)['mode'], 'manual')
        with self.post('/api/actuators', {'actuator': 'lighting', 'enabled': False}) as response:
            self.assertIs(json.load(response)['lighting'], True)  # L'état réel attend la Yún.
        with self.post('/api/ingest', {'sensor': sensor,
                                       'readings': {'light_raw': 950, 'lighting': 1}}) as response:
            command = json.load(response)['command']
        self.assertRegex(command, r'^lighting 0 \d+$')
        with self.post('/api/ingest', {'sensor': sensor, 'ack': int(command.split()[-1]),
                                       'readings': {'light_raw': 950, 'lighting': 0}}) as response:
            self.assertEqual(json.load(response)['command'], '')

        with self.post('/api/mode', {'mode': 'automatic'}) as response:
            self.assertEqual(json.load(response)['mode'], 'automatic')
        with self.post('/api/ingest', {'sensor': sensor,
                                       'readings': {'light_raw': 950, 'lighting': 0}}) as response:
            self.assertRegex(json.load(response)['command'], r'^lighting 1 \d+$')
        with self.assertRaises(HTTPError) as error:
            self.post('/api/actuators', {'actuator': 'pump', 'enabled': True})
        self.assertEqual(error.exception.code, 409)

    def test_rejections(self):
        cases = [
            ('/api/actuators', 'POST', 400),      # corps JSON obligatoire
            ('/%2e%2e/secret.txt', 'GET', 404),   # remontée de répertoire
            ('/api/inconnu', 'GET', 404),
        ]
        for path, method, expected in cases:
            with self.subTest(path=path):
                with self.assertRaises(HTTPError) as error:
                    urlopen(Request(self.base + path, method=method))
                self.assertEqual(error.exception.code, expected)

    def test_invalid_payload_returns_400(self):
        with self.assertRaises(HTTPError) as error:
            self.post('/api/ingest', {'readings': {'temperature': 20}})
        self.assertEqual(error.exception.code, 400)


class TokenTests(TemporaryDatabase):
    def setUp(self):
        super().setUp()
        self.config = make_config(self.db_path, token='secret-workshop')
        self.server = ThreadingHTTPServer(
            ('127.0.0.1', 0), partial(Handler, static_dir=None, config=self.config))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = 'http://127.0.0.1:{}'.format(self.server.server_port)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        super().tearDown()

    def _post(self, token=None):
        headers = {'Content-Type': 'application/json'}
        if token is not None:
            headers['X-Auth-Token'] = token
        payload = json.dumps({'sensor': 'serre-01', 'readings': {'temperature': 23.4}})
        return urlopen(Request(self.base + '/api/ingest', data=payload.encode('utf-8'),
                               method='POST', headers=headers))

    def test_token_is_enforced(self):
        for token in (None, 'mauvais-jeton'):
            with self.subTest(token=token):
                with self.assertRaises(HTTPError) as error:
                    self._post(token)
                self.assertEqual(error.exception.code, 401)
        with self._post('secret-workshop') as response:
            self.assertEqual(response.status, 201)


if __name__ == '__main__':
    unittest.main(verbosity=2)
