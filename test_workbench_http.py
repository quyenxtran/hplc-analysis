"""Exercise the real local HTTP boundary and its origin/revision checks."""
import json
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from hplc.workbench.server import make_server
from hplc.workbench.state import Workbench


class WorkbenchHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server, cls.token = make_server(Workbench())
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_assets_and_authenticated_state(self):
        with urlopen(self.url) as response:
            self.assertIn(b"HPLC workbench", response.read())
            self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])
        with urlopen(Request(self.url + "/api/state", headers={"X-Session": self.token})) as response:
            state = json.load(response)
        self.assertEqual(state["peaks"][0]["peak_id"], "envelope")
        for name in ("app.js", "actions.js", "pointer.js", "chart.js", "style.css"):
            with urlopen(self.url + "/" + name) as response:
                self.assertEqual(response.status, 200)

    def test_unauthenticated_cross_origin_and_unknown_path_rejected(self):
        for headers in ({}, {"X-Session": self.token, "Origin": "https://example.org"},
                        {"X-Session": self.token, "Host": "attacker.invalid"}):
            with self.assertRaises(HTTPError) as error:
                urlopen(Request(self.url + "/api/state", headers=headers))
            self.assertEqual(error.exception.code, 403)
        with self.assertRaises(HTTPError) as error:
            urlopen(self.url + "/../AGENTS.md")
        self.assertEqual(error.exception.code, 404)

    def test_real_post_edit_and_bad_request(self):
        with urlopen(Request(self.url + "/api/state", headers={"X-Session": self.token})) as response:
            state = json.load(response)
        data = {"revision": state["revision"], "action": "edit", "op": "move_baseline",
                "parameters": {"peak_id": "envelope", "start_mv": .087}}
        headers = {"X-Session": self.token, "Content-Type": "application/json"}
        with urlopen(Request(self.url + "/api/action", data=json.dumps(data).encode(), headers=headers)) as response:
            result = json.load(response)
        self.assertEqual(result["state"]["revision"], state["revision"] + 1)
        with self.assertRaises(HTTPError) as error:
            urlopen(Request(self.url + "/api/action", data=b"[]", headers=headers))
        self.assertEqual(error.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
