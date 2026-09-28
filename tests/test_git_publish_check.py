import re

from research_v2.git_publish_check import PATTERNS


def test_key_pattern_requires_a_token_boundary_but_accepts_real_key_position():
    synthetic = b"sk-" + b"A" * 40
    assert any(re.search(p, b'"api_key":"' + synthetic + b'"') for p in PATTERNS)
    assert not any(re.search(p, b"gAAAAA_randomcipher" + synthetic + b"cipher_tail") for p in PATTERNS)


def test_private_key_header_is_blocked():
    header = b"-----BEGIN OPENSSH " + b"PRIVATE KEY-----"
    assert any(re.search(p, header) for p in PATTERNS)
