Category:
Attribute & Local Conflict Errors

Expected Issues:

1. OSPF advertises a network associated with an administratively disabled interface.

   Configuration:
   router ospf 1
    network 192.168.20.0 0.0.0.255 area 0

   Related Interface:
   GigabitEthernet0/2
    ip address 192.168.20.1 255.255.255.0
    shutdown

   Issue:
   The network 192.168.20.0/24 is included in OSPF, but the corresponding interface is administratively down.

2. Default route points to an unusable interface.

   Configuration:
   ip route 0.0.0.0 0.0.0.0 GigabitEthernet0/3

   Related Interface:
   GigabitEthernet0/3
    shutdown

   Issue:
   The default route forwards traffic to an interface that is administratively disabled and cannot forward packets.

3. Incomplete NAT configuration.

   Configuration:
   interface GigabitEthernet0/0
    ip nat inside

   interface GigabitEthernet0/1
    ip nat inside

   ip nat inside source list 1 interface GigabitEthernet0/3 overload

   Issue:
   NAT inside interfaces are configured, but no interface is configured with 'ip nat outside'. NAT translation cannot operate correctly.