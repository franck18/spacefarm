"""Vérifie le contrôle d’accès et la panne du relais IA."""
import unittest
from unittest.mock import patch
from urllib.error import URLError
import ai_proxy


class AssistantProxyTests(unittest.TestCase):
    def test_no_code_never_contacts_bridge(self):
        with patch('ai_proxy.urlopen') as request:
            self.assertEqual(ai_proxy.forward('ask', {}, '')[0], 401)
            request.assert_not_called()

    def test_unknown_action_never_contacts_bridge(self):
        with patch('ai_proxy.urlopen') as request:
            self.assertEqual(ai_proxy.forward('shell', {}, 'code')[0], 404)
            request.assert_not_called()

    def test_offline_pc_returns_clear_error(self):
        with patch('ai_proxy.urlopen', side_effect=URLError('offline')):
            status, body = ai_proxy.forward('status', {}, 'code')
            self.assertEqual(status, 503)
            self.assertIn('tunnel SSH', body['error'])
