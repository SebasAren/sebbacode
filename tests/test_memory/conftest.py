"""pytest configuration for test_memory package.

This conftest provides fixtures and configuration for all memory tests.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_invoke_with_timeout():
    """Mock LLM calls for all tests in this package.
    
    Tests that need real LLM calls should explicitly unmock this fixture.
    Tests that need specific LLM responses should patch as needed within their test.
    """
    mock_response = MagicMock()
    mock_response.content = "Mocked summary with enough words to pass the validation check for testing purposes."

    with patch("sebba_code.memory.summarize.invoke_with_timeout", return_value=mock_response), \
         patch("sebba_code.memory.summarize.get_cheap_llm", return_value=MagicMock()):
        yield


@pytest.fixture
def tmp_memory_root(tmp_path):
    """Provide a temporary directory for memory storage."""
    from sebba_code.memory.layers import MemoryLayer
    from sebba_code.memory.hook import reset_executor
    
    yield tmp_path
    
    # Cleanup
    reset_executor()
