from utils.redact import mask_proxy


def test_credentials_are_hidden():
    masked = mask_proxy("http://user:secret@1.2.3.4:8080")
    assert "secret" not in masked and "user" not in masked
    assert masked == "http://***@1.2.3.4:8080"


def test_plain_proxy_and_direct():
    assert mask_proxy("socks5://proxy.local:1080") == "socks5://proxy.local:1080"
    assert mask_proxy(None) == "DIRECT"
    assert mask_proxy("") == "DIRECT"


def test_garbage_is_not_echoed():
    assert mask_proxy("not a url with password") == "<invalid proxy url>"
