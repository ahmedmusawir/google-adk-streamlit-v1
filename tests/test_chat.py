# tests/test_chat.py

import pytest
import json
import requests
from unittest.mock import Mock

# We need to tell pytest where to find the chat.py file.
# This assumes your project structure allows importing from the root.
# If this fails, we may need a __init__.py in the root or to adjust sys.path.
from chat import call_n8n_webhook

# Test Scenario 1: A successful call to the n8n webhook
def test_call_n8n_webhook_success(mocker):
    """
    Tests the happy path: the webhook responds with a valid,
    double-layered JSON and our function parses it correctly.
    """
    # 1. Prepare the mock response from n8n
    # This is the inner JSON object
    inner_data = {"message": "Hello from the agent"}
    # This is the outer JSON object, where 'data' is a string
    outer_data = {"data": json.dumps(inner_data)}

    # 2. Configure the mock object to simulate requests.post
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = outer_data
    # This line intercepts any call to 'requests.post' and returns our mock_response instead
    mocker.patch('requests.post', return_value=mock_response)

    # 3. Call the function we are testing
    result = call_n8n_webhook("test_agent", "test_message", "test_user")

    # 4. Assert that the result is what we expect
    assert result == "Hello from the agent"
    print("\n--- Test Passed: Successfully parsed double JSON response. ---")

# Test Scenario 2: The n8n webhook returns an HTTP error
def test_call_n8n_webhook_http_error(mocker):
    """
    Tests the failure path: the webhook is down or returns an error,
    and our function handles it gracefully.
    """
    # 1. Configure the mock to simulate a server error
    mock_response = Mock()
    # This function makes the mock raise an HTTPError when checked
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError
    mocker.patch('requests.post', return_value=mock_response)

    # 2. Call the function
    result = call_n8n_webhook("test_agent", "test_message", "test_user")

    # 3. Assert that our function returned the correct error message
    assert "Error: Could not reach the n8n orchestrator." in result
    print("\n--- Test Passed: Correctly handled HTTP error. ---")