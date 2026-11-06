import ipaddress
def test_app_subnet():
    net = ipaddress.ip_network("10.20.0.0/22")
    assert net.num_addresses == 1024
    assert str(net.network_address) == "10.20.0.0"
    assert str(net.broadcast_address) == "10.20.3.255"
def test_public_subnet():
    net = ipaddress.ip_network("10.20.4.0/24")
    assert net.num_addresses == 256
def test_management_subnet():
    net = ipaddress.ip_network("10.20.5.128/27")
    assert net.num_addresses == 32
