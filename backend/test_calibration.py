"""Vérifie les références et l'absence de mélange entre ADC et lux."""
import unittest
from calibration import relative_light, reservoir_level
from test_server import TemporaryDatabase
from routes import snapshot


class LightConversionTests(unittest.TestCase):
    def test_reference_points_and_clamping(self):
        self.assertEqual(relative_light(1015), 0)
        self.assertEqual(relative_light(617.5), 50)
        self.assertEqual(relative_light(220), 100)
        self.assertEqual(relative_light(0), 100)
        for invalid in (None, -1, 1024, float('nan')):
            self.assertIsNone(relative_light(invalid))


class WaterConversionTests(unittest.TestCase):
    def test_reference_points_and_clamping(self):
        self.assertEqual(reservoir_level(0), 0)
        self.assertEqual(reservoir_level(358.5), 50)
        self.assertEqual(reservoir_level(478), 66.7)
        self.assertEqual(reservoir_level(717), 100)
        self.assertEqual(reservoir_level(800), 100)
        for invalid in (None, -1, 1024, float('nan')):
            self.assertIsNone(reservoir_level(invalid))


class LightSnapshotTests(TemporaryDatabase):
    def test_raw_light_replaces_legacy_lux_in_card_and_history(self):
        self.ingest(light=758, light_raw=617.5)
        result = snapshot(self.config)
        self.assertEqual(result['measurements']['light']['value'], 50)
        self.assertEqual(result['measurements']['light']['unit'], '%')
        self.assertEqual(result['history'][0]['light'], 50)

    def test_legacy_lux_cannot_be_presented_as_percent(self):
        self.ingest(light=758)
        result = snapshot(self.config)
        self.assertIsNone(result['measurements']['light']['value'])
        self.assertIsNone(result['history'][0]['light'])

    def test_stale_raw_light_is_hidden(self):
        self.ingest(light_raw=617.5)
        self.config['stale'] = -1
        self.assertIsNone(snapshot(self.config)['measurements']['light']['value'])


class WaterSnapshotTests(TemporaryDatabase):
    def test_raw_water_replaces_legacy_percent_in_card_history_and_volume(self):
        self.ingest(water=84, water_raw=358.5)
        result = snapshot(self.config)
        self.assertEqual(result['measurements']['water']['value'], 50)
        self.assertEqual(result['measurements']['water']['unit'], '%')
        self.assertEqual(result['history'][0]['water'], 50)
        self.assertEqual(result['reservoirLiters'], 5)

    def test_legacy_water_cannot_be_presented_as_real_measurement(self):
        self.ingest(water=84)
        result = snapshot(self.config)
        self.assertIsNone(result['measurements']['water']['value'])
        self.assertIsNone(result['history'][0]['water'])
