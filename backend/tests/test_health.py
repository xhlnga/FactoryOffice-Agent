import unittest

from app.api.v1.endpoints.health import check_health


class HealthEndpointTest(unittest.TestCase):
    """健康检查接口测试。"""

    def test_health_returns_ok(self) -> None:
        self.assertEqual(check_health(), {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
