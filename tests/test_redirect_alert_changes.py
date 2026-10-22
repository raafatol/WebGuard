from app.services.change_detector import detect_redirect_changes, detect_changes


def a(status):
    return {'redirect': {'status': status}, 'headers': {}, 'http_status': 200}


def test_lost_redirect():
    for status in ('no_redirect', 'ends_on_http'):
        result = detect_redirect_changes(a('redirects_to_https'), a(status))
        assert len(result) == 1
        assert result[0]['type'] == 'redirect_https_lost'
        assert result[0]['severity'] == 'warning'


def test_restored_redirect():
    result = detect_redirect_changes(a('no_redirect'), a('redirects_to_https'))
    assert len(result) == 1 and result[0]['type'] == 'redirect_https_restored'


def test_unchanged_does_not_repeat():
    for status in ('no_redirect', 'ends_on_http', 'redirects_to_https'):
        assert detect_redirect_changes(a(status), a(status)) == []


def test_unknown_does_not_create_false_alerts():
    for status in ('connection_error', 'redirect_loop', 'external_redirect_unverified',
                   'too_many_redirects', 'http_error_status', 'unsupported_redirect', 'unknown'):
        assert detect_redirect_changes(a('redirects_to_https'), a(status)) == []
        assert detect_redirect_changes(a(status), a('no_redirect')) == []
        assert detect_redirect_changes(a(status), a('redirects_to_https')) == []


def test_old_record_without_redirect():
    assert detect_redirect_changes({}, a('no_redirect')) == []
    assert detect_redirect_changes(a('redirects_to_https'), {'redirect': None}) == []


def test_existing_header_detection_preserved():
    before = {'http_status': 200, 'headers': {'HSTS': {'present': True}}}
    after = {'http_status': 200, 'headers': {'HSTS': {'present': False}}}
    assert detect_changes(before, after)[0]['type'] == 'header_removed'
