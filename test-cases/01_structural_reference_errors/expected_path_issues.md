# Oczekiwane bledne sciezki

Dokument opisuje referencyjne wartosci `hasIssue` dla scenariusza
`01_structural_reference_errors`.

Etykiety odnosza sie do docelowej konfiguracji scenariusza po usunieciu
niezamierzonych problemow, takich jak `login` VTY bez hasla. Sciezki nie
wymienione w tym dokumencie powinny otrzymac `hasIssue=false`.

## Problem 1: niezdefiniowana ACL 100

### Sciezka z `hasIssue=true`

```text
interface GigabitEthernet0/1 ->  ip access-group 100 in
```

Interfejs odwoluje sie do ACL 100, ale taka lista nie jest zdefiniowana
w konfiguracji.

## Problem 2: niezdefiniowana ACL `NAT_TRAFFIC`

### Sciezka z `hasIssue=true`

```text
ip nat inside source list NAT_TRAFFIC interface GigabitEthernet0/0 overload
```

Regula NAT odwoluje sie do nieistniejacej ACL `NAT_TRAFFIC`.

## Problem 3: nieuzywana ACL 150

Wszystkie ponizsze sciezki powinny otrzymac `hasIssue=true` jako jedna grupe
reprezentujaca jeden blad logiczny: zdefiniowana, ale nigdzie nieuzywana ACL
150.

```text
access-list 150 remark Legacy Internet Edge Filter
access-list 150 deny tcp any any eq telnet
access-list 150 deny tcp any any eq ftp
access-list 150 deny tcp any any eq www
access-list 150 permit ip any any
```

Kazda z tych sciezek jest czescia tego samego obiektu ACL. Nie nalezy liczyc
ich jako pieciu niezaleznych bledow.

## Podsumowanie

| Liczba bledow logicznych | Liczba sciezek z `hasIssue=true` |
|---:|---:|
| 3 | 7 |

Adresy IP, role `ip nat inside`/`ip nat outside`, wylaczony nieuzywany
interfejs, `Vlan1` oraz poprawnie zabezpieczone linie konsoli i VTY powinny
pozostac oznaczone jako `false`.
