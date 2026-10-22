"""Inspección limitada de redirecciones HTTP -> HTTPS.

Sigue solo el mismo host y puertos estándar. No sustituye la protección SSRF
por resolución/pinning de IP que requiere una aplicación multiusuario pública.
"""
import ipaddress
import re
from urllib.parse import urljoin, urlsplit
import httpx

_REDIRECTS = {301, 302, 303, 307, 308}
_MAX_HOPS = 5
_HOST_RE = re.compile(r"(?=.{1,253}$)[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$")


def _valid_host(domain):
    if not isinstance(domain, str) or not _HOST_RE.fullmatch(domain) or '..' in domain:
        return False
    try:
        ipaddress.ip_address(domain)
        return False
    except ValueError:
        return True


def check_http_redirect(domain):
    result = {
        "domain": domain, "status": "unknown", "http_status": None,
        "location": None, "error": None, "hops": [], "final_url": None,
        "hop_count": 0,
    }
    if not _valid_host(domain):
        result.update(status="invalid_domain", error="InvalidDomain")
        return result

    origin = domain.lower().rstrip('.')
    url = f"http://{origin}/"
    visited = set()
    try:
        with httpx.Client(timeout=httpx.Timeout(10.0, connect=5.0),
                          follow_redirects=False, trust_env=False) as client:
            for _ in range(_MAX_HOPS + 1):
                if url in visited:
                    result["status"] = "redirect_loop"
                    break
                visited.add(url)
                response = client.get(url)
                code = response.status_code
                result["http_status"] = code
                result["final_url"] = url
                location = response.headers.get("location")
                if code not in _REDIRECTS or not location:
                    if urlsplit(url).scheme == "https" and 200 <= code < 400:
                        result["status"] = "redirects_to_https"
                    elif urlsplit(url).scheme == "http" and 200 <= code < 400:
                        result["status"] = "no_redirect" if not result["hops"] else "ends_on_http"
                    else:
                        result["status"] = "http_error_status" if code >= 400 else "unknown"
                    break

                result["location"] = location[:500]
                target_url = urljoin(url, location)
                target = urlsplit(target_url)
                hop = {"from": url, "status": code, "to": target_url[:500]}
                result["hops"].append(hop)
                result["hop_count"] = len(result["hops"])

                if target.scheme not in ("http", "https") or not target.hostname:
                    result["status"] = "unsupported_redirect"
                    break
                if target.username is not None or target.password is not None:
                    result["status"] = "unsupported_redirect"
                    break
                try:
                    port = target.port
                except ValueError:
                    result["status"] = "unsupported_redirect"
                    break
                if port not in (None, 80 if target.scheme == "http" else 443):
                    result["status"] = "unsupported_redirect"
                    break
                if target.hostname.lower().rstrip('.') != origin:
                    result["status"] = "external_redirect_unverified"
                    break
                if result["hop_count"] >= _MAX_HOPS:
                    result["status"] = "too_many_redirects"
                    break
                url = target_url
    except httpx.HTTPError as exc:
        result["error"] = type(exc).__name__
        result["status"] = "connection_error"
    return result
