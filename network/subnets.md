# Subnets - 10.20.0.0/16

Allocated largest to smallest, starting at 10.20.0.0, smallest prefix that fits. Usable hosts = 2^(32-prefix) - 2.

| Subnet | Network | Prefix | Usable range | Broadcast | Usable hosts |
|---|---|---|---|---|---|
| app, 1000 needed | 10.20.0.0 | /22 | 10.20.0.1 - 10.20.3.254 | 10.20.3.255 | 1022 |
| public, 250 needed | 10.20.4.0 | /24 | 10.20.4.1 - 10.20.4.254 | 10.20.4.255 | 254 |
| data, 100 needed | 10.20.5.0 | /25 | 10.20.5.1 - 10.20.5.126 | 10.20.5.127 | 126 |
| management, 20 needed | 10.20.5.128 | /27 | 10.20.5.129 - 10.20.5.158 | 10.20.5.159 | 30 |

Working: app needs 1000, next power of 2 is 1024, so /22. public needs 250, next is 256, so /24. data needs 100, next is 128, so /25. management needs 20, next is 32, so /27. Each subnet starts right after the previous one. Next free address is 10.20.5.160.

## Why a stateless NACL needs reply rules

A NACL does not remember connections. A stateful firewall lets the reply back automatically, a NACL does not. So every reply is a new packet and needs its own rule. That is why inbound allows TCP 1024-65535 from the app subnet, and outbound allows TCP 1024-65535 to anywhere, for replies to clients on their ephemeral ports.

## Why rule order matters

Rules are checked lowest number first, first match wins. The deny for 198.51.100.0/24 is rule 100, before the allow for 80 and 443 at 110 and 120. If the allow was first, traffic from the abusive range on port 443 would be allowed. With deny first, it is blocked even on web ports.
