from backend.main import _parse_ai_response


def test_parse_ai_response_handles_markdown_json_block() -> None:
    response = """```json
{
  \"cause\": \"Memory leak in the checkout worker\",
  \"impact\": \"Checkout requests are timing out for 20% of users\",
  \"fix\": \"Roll back the new queue worker and restart the service\"
}
```"""

    parsed = _parse_ai_response(response)

    assert parsed["cause"] == "Memory leak in the checkout worker"
    assert parsed["impact"] == "Checkout requests are timing out for 20% of users"
    assert parsed["fix"] == "Roll back the new queue worker and restart the service"
