import tempfile
import unittest
from pathlib import Path
from app import app

class FinTrackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        app.config.update(TESTING=True, DATABASE=str(Path(self.temp.name)/'test.db'), SECRET_KEY='test-only-secret')
        self.client = app.test_client()
        self.client.get('/')
        with self.client.session_transaction() as sess:
            self.csrf = sess['csrf']

    def tearDown(self):
        self.temp.cleanup()

    def post(self, path, data):
        return self.client.post(path, json=data, headers={'X-CSRF-Token': self.csrf})

    def test_registration_and_private_transactions(self):
        r = self.post('/api/register', {'email':'example@test.com','password':'long-test-password-123'})
        self.assertEqual(r.status_code, 201)
        self.csrf = r.json['csrf']
        r = self.post('/api/transactions', {'description':'Groceries','amount':4500,'type':'expense','category':'Food','date':'2026-11-10'})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(len(self.client.get('/api/transactions').json), 1)
        self.assertEqual(self.client.get('/api/insights?month=2026-11').json['expenses'], 4500)
        self.assertIn('Groceries', self.client.get('/api/export.csv').get_data(as_text=True))
        self.post('/api/logout', {})
        self.assertEqual(self.client.get('/api/transactions').status_code, 401)

    def test_csrf_required(self):
        self.assertEqual(self.client.post('/api/register', json={}).status_code, 403)

if __name__ == '__main__':
    unittest.main()
