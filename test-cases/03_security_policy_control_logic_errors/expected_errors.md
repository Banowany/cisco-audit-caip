Category:
Security Policy & Control Logic Errors

Expected Issues:

1. ACL rule shadowing makes SSH restriction ineffective.

   Configuration:
   access-list 110 permit ip any any
   access-list 110 deny tcp any any eq 22

   Issue:
   ACLs are processed sequentially from top to bottom. The rule 'permit ip any any' matches all IP traffic, including SSH traffic (TCP port 22). Therefore, the subsequent deny rule is never reached and has no effect.

2. Password encryption is not enabled.

   Configuration:
   line console 0
    password admin123
    login

   line vty 0 4
    password telnet123
    login

   Missing Configuration:
   service password-encryption

   Issue:
   The router stores line passwords in plain text because password encryption is not enabled. Anyone with access to the configuration file can read these credentials directly.

3. Weak privileged EXEC authentication mechanism is used.

   Configuration:
   enable password cisco

   Missing Configuration:
   enable secret <password>

   Issue:
   The configuration uses the legacy 'enable password' mechanism instead of the more secure 'enable secret'. This provides weaker protection for privileged access to the device.

4. Remote administrative access is insufficiently restricted.

   Configuration:
   line vty 0 4
    password telnet123
    login

   Missing Configuration:
   transport input ssh
   access-class <ACL> in

   Issue:
   Remote access lines do not restrict management protocols and do not limit source IP addresses. Telnet access may be permitted and any reachable host can attempt administrative connections to the router.