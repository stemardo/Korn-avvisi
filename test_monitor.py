"""Verifica segnali ambigui, errori e notifiche su cambi di disponibilita."""
import copy
import datetime as dt
import unittest
from unittest.mock import patch

import monitor as m

NOW = dt.datetime(2026, 11, 11, 12, tzinfo=dt.timezone.utc)


def event(stock=False):
    return {'productId': m.EVENT_ID, 'productGroupId': m.GROUP_ID, 'name': 'Korn',
            'status': 'Available', 'inStock': stock,
            'typeAttributes': {'liveEntertainment': {
                'startDate': m.EVENT_START.isoformat(),
                'location': {'name': 'Unipol Forum'}}}}


class MonitorTests(unittest.TestCase):
    def test_available_label_without_stock_never_means_available(self):
        self.assertIs(m.read_stock({'products': [event(False)]}), False)
        for value in (None, 'true', 1):
            with self.subTest(value=value):
                with self.assertRaises(m.MonitorError):
                    m.read_stock({'products': [event(value)]})

    def test_other_event_date_venue_or_duplicate_is_unknown(self):
        for change in ('id', 'date', 'venue', 'duplicate', 'cancelled'):
            p = event(True)
            if change == 'id':
                p['productId'] = 'other'
            elif change == 'date':
                p['typeAttributes']['liveEntertainment']['startDate'] = '2026-11-22T21:00:00+01:00'
            elif change == 'venue':
                p['typeAttributes']['liveEntertainment']['location']['name'] = 'Other'
            elif change == 'cancelled':
                p['status'] = 'Cancelled'
            with self.subTest(change=change):
                with self.assertRaises(m.MonitorError):
                    m.read_stock({'products': [p, p] if change == 'duplicate' else [p]})

    def test_notifications_only_on_activation_and_new_stock(self):
        messages = []
        state = m.initial_state()
        for stock in (False, False, True, True, False, True):
            state = m.update_known(state, stock, NOW, messages.append)
        self.assertEqual(len(messages), 3)
        self.assertIn('attivato', messages[0])
        self.assertTrue(all('tornati disponibili' in msg for msg in messages[1:]))

    def test_failure_keeps_stock_and_throttles_outage_messages(self):
        messages = []
        state = m.update_known(m.initial_state(), True, NOW, lambda _: None)
        for _ in range(10):
            state = m.update_failure(state, NOW, messages.append)
        self.assertIs(state['last_stock'], True)
        self.assertEqual(len(messages), 1)
        self.assertIn('sconosciuta', messages[0])
        state = m.update_failure(state, NOW + dt.timedelta(days=1), messages.append)
        self.assertEqual(len(messages), 2)
        recovered = []
        m.update_known(state, True, NOW + dt.timedelta(days=1), recovered.append)
        self.assertEqual(len(recovered), 1)
        self.assertIn('ripreso', recovered[0])

    def test_failed_message_does_not_mark_availability_as_notified(self):
        state = m.update_known(m.initial_state(), False, NOW, lambda _: None)
        previous = copy.deepcopy(state)
        def failure(_):
            raise m.MonitorError('Telegram: HTTP 500.')
        with self.assertRaises(m.MonitorError):
            m.update_known(state, True, NOW, failure)
        self.assertEqual(state, previous)
        messages = []
        m.update_known(state, True, NOW, messages.append)
        self.assertEqual(len(messages), 1)

    def test_expiry_disables_schedule_before_requesting_event_or_secrets(self):
        with patch.object(m, 'github') as github, patch.object(m, 'fetch_stock') as fetch, patch.object(m, 'log'):
            m.run(m.EVENT_START)
        fetch.assert_not_called()
        github.assert_called_once_with('/actions/workflows/monitor.yml/disable', method='PUT')

    def test_http_exception_cannot_leak_bot_token(self):
        with patch('urllib.request.urlopen', side_effect=OSError('token-esempio-segreto')):
            with self.assertRaises(m.MonitorError) as caught:
                m.request_json('https://example.com', label='Telegram')
        self.assertNotIn('token-esempio-segreto', str(caught.exception))


if __name__ == '__main__':
    unittest.main()
