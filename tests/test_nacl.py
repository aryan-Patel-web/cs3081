import json
def test_nacl_file_exists_and_deny_first():
    data = json.load(open("network/nacl.json"))
    assert data["inbound"][0]["rule"] == 100
    assert data["inbound"][0]["action"] == "deny"
    assert data["inbound"][0]["cidr"] == "198.51.100.0/24"
    assert data["outbound"][0]["port_from"] == 8000
