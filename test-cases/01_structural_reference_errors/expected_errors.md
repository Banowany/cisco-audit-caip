Expected Errors:

1. Undefined ACL referenced by interface

Description:
An interface applies ACL 100 using the command:

ip access-group 100 in

However, ACL 100 is not defined anywhere in the configuration. The interface therefore references a non-existent object.

Classification:
Structural & Reference Error

---

2. Undefined ACL referenced by NAT configuration

Description:
The NAT configuration contains the command:

ip nat inside source list NAT_TRAFFIC interface GigabitEthernet0/0 overload

However, the access list NAT_TRAFFIC is not defined in the configuration. As a result, the NAT rule references a missing object and cannot correctly identify traffic for translation.

Classification:
Structural & Reference Error

---

3. Unused ACL definition

Description:
ACL 150 is fully defined in the configuration but is never referenced by any interface, VTY line, NAT rule, routing policy, or other service.

The ACL therefore represents an orphaned configuration structure that has no operational effect.

Classification:
Structural & Reference Error
