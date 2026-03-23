import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class StoryOneSmokeTests(unittest.TestCase):
    def test_v1_process_route_wiring_exists(self) -> None:
        process_source = (ROOT / 'app' / 'api' / 'v1' / 'process.py').read_text(encoding='utf-8')
        router_source = (ROOT / 'app' / 'api' / 'v1' / 'router.py').read_text(encoding='utf-8')
        main_source = (ROOT / 'app' / 'main.py').read_text(encoding='utf-8')

        self.assertIn("@router.post('/process'", process_source)
        self.assertIn('prefix="/v1"', router_source)
        self.assertIn('include_router(process_router)', router_source)
        self.assertIn('app.include_router(api_v1_router)', main_source)

    def test_process_response_envelope_fields_exist(self) -> None:
        process_source = (ROOT / 'app' / 'api' / 'v1' / 'process.py').read_text(encoding='utf-8')

        self.assertIn("status='success'", process_source)
        self.assertIn('request_id=str(uuid4())', process_source)
        self.assertIn('payload=ProcessPayload(', process_source)


if __name__ == '__main__':
    unittest.main()
