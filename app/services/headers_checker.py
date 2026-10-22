"""HTTP checks with explicit distinction between absence and failure."""
import httpx

SECURITY_HEADERS = {
    'strict-transport-security': 'HSTS',
    'content-security-policy': 'CSP',
    'x-frame-options': 'X-Frame-Options',
    'x-content-type-options': 'X-Content-Type-Options',
    'referrer-policy': 'Referrer-Policy',
    'permissions-policy': 'Permissions-Policy',
}


def check_headers(domain):
    # domain must already be validated by validate_domain; never accept a URL here.
    url = f'https://{domain}'
    try:
        with httpx.Client(timeout=httpx.Timeout(10.0, connect=5.0),
                          follow_redirects=True, max_redirects=5,
                          trust_env=False, verify=True) as client:
            response = client.get(url)
            results = {}
            for key, name in SECURITY_HEADERS.items():
                value = response.headers.get(key)
                results[name] = {'present': value is not None, 'value': value}
            return {
                'domain': domain, 'status': 'success',
                'http_status': response.status_code,
                'headers': results,
                'present_count': sum(v['present'] for v in results.values()),
                'total_headers': len(SECURITY_HEADERS), 'error': None,
                'error_type': None,
            }
    except httpx.HTTPError as exc:
        # The database stores unknown as NULL; do not turn it into 0 headers.
        return {
            'domain': domain, 'status': 'error', 'http_status': None,
            'headers': {name: {'present': None, 'value': None}
                        for name in SECURITY_HEADERS.values()},
            'present_count': None, 'total_headers': len(SECURITY_HEADERS),
            'error': str(exc), 'error_type': type(exc).__name__,
        }
