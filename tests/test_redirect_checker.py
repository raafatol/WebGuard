from unittest.mock import patch
from app.services.redirect_checker import check_http_redirect

class FakeResponse:
    def __init__(self, code, location=None):
        self.status_code = code
        self.headers = {"location": location} if location else {}

class FakeClient:
    def __init__(self, mapping, **kwargs):
        self.mapping = mapping
        self.calls = []
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def get(self, url):
        self.calls.append(url)
        return self.mapping[url]

def run(mapping, domain="example.com"):
    fake = FakeClient(mapping)
    with patch("app.services.redirect_checker.httpx.Client", return_value=fake):
        result = check_http_redirect(domain)
    return result, fake.calls

def test_redirect_https_reaches_200():
    r, calls = run({"http://example.com/": FakeResponse(301, "https://example.com/"), "https://example.com/": FakeResponse(200)})
    assert r["status"] == "redirects_to_https" and r["hop_count"] == 1
    assert len(calls) == 2

def test_https_target_error_is_not_success():
    r, _ = run({"http://example.com/": FakeResponse(301, "https://example.com/"), "https://example.com/": FakeResponse(503)})
    assert r["status"] == "http_error_status"

def test_http_200():
    r, _ = run({"http://example.com/": FakeResponse(200)})
    assert r["status"] == "no_redirect"

def test_relative_then_https():
    r, _ = run({"http://example.com/": FakeResponse(302, "/start"), "http://example.com/start": FakeResponse(301, "https://example.com/"), "https://example.com/": FakeResponse(200)})
    assert r["status"] == "redirects_to_https" and r["hop_count"] == 2

def test_loop():
    r, _ = run({"http://example.com/": FakeResponse(302, "/again"), "http://example.com/again": FakeResponse(302, "/")})
    assert r["status"] == "redirect_loop"

def test_external_not_followed():
    r, calls = run({"http://example.com/": FakeResponse(301, "https://other.example/")})
    assert r["status"] == "external_redirect_unverified" and len(calls) == 1

def test_nonstandard_port_not_followed():
    r, calls = run({"http://example.com/": FakeResponse(302, "http://example.com:8080/admin")})
    assert r["status"] == "unsupported_redirect" and len(calls) == 1

def test_invalid_domain():
    r, calls = run({}, domain="127.0.0.1")
    assert r["status"] == "invalid_domain" and not calls

def test_redirect_ends_http():
    r, _ = run({"http://example.com/": FakeResponse(302, "/landing"), "http://example.com/landing": FakeResponse(200)})
    assert r["status"] == "ends_on_http"

def test_too_many_redirects():
    mapping = {}
    for i in range(6):
        source = "http://example.com/" if i == 0 else f"http://example.com/{i}"
        mapping[source] = FakeResponse(302, f"/{i+1}")
    r, calls = run(mapping)
    assert r["status"] == "too_many_redirects" and len(calls) == 5
