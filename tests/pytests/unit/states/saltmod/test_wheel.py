import pytest

import salt.states.saltmod as saltmod
import salt.utils.state
from tests.support.mock import MagicMock, patch


@pytest.fixture
def configure_loader_modules(minion_opts):
    return {
        saltmod: {
            "__env__": "base",
            "__opts__": minion_opts,
            "__utils__": {"state.check_result": salt.utils.state.check_result},
        },
    }


def test_wheel():
    """
    Test to execute a wheel module on the master
    """
    name = "state"

    expected = {
        "changes": {"return": True},
        "name": "state",
        "result": True,
        "comment": "Wheel function 'state' executed.",
    }
    with patch.dict(
        saltmod.__salt__, {"saltutil.wheel": MagicMock(return_value={"return": True})}
    ):
        ret = saltmod.wheel(name)
        assert ret == expected
