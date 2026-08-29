# Oczekiwane bledne sciezki

Dokument opisuje referencyjne wartosci `hasIssue` dla scenariusza
`03_security_policy_control_logic_errors`.

Sciezki nie wymienione w tym dokumencie powinny otrzymac `hasIssue=false`.

## Problem 1: wylaczone szyfrowanie hasel

### Sciezka z `hasIssue=true`

```text
no service password-encryption
```

W konfiguracji wystepuja hasla konsoli i VTY, ale ich szyfrowanie jest
wylaczone. Hasla sa przechowywane jawnie.

## Problem 2: uzycie `enable password`

### Sciezka z `hasIssue=true`

```text
enable password cisco
```

Uzywany jest slabszy, starszy mechanizm uwierzytelniania uprzywilejowanego
oraz latwe do odgadniecia haslo.

## Problem 3: shadowing reguly ACL 110

Obie ponizsze sciezki powinny otrzymac `hasIssue=true` jako jedna grupe
reprezentujaca jeden blad logiczny:

```text
access-list 110 permit ip any any
access-list 110 deny tcp any any eq 22
```

Pierwsza regula dopasowuje caly ruch i dlatego pozniejsza regula blokujaca
SSH jest nieskuteczna. Samo zastosowanie ACL do interfejsu nie jest bledem.

## Problem 4: niezabezpieczony dostep VTY

Obie ponizsze sciezki powinny otrzymac `hasIssue=true` jako jedna grupe
reprezentujaca problem calego bloku VTY:

```text
line vty 0 4 ->  password telnet123
line vty 0 4 ->  login
```

Blok VTY wykorzystuje slabe, jawne haslo i nie ogranicza protokolu ani zrodel
dostepu przez `transport input ssh` oraz `access-class`.

Polecenie `login` nie jest bledem skladniowym. Jest oznaczane jako element
wadliwej grupy VTY, poniewaz problem dotyczy calego bloku konfiguracji.

## Problem 5: jawne i slabe haslo konsoli

### Sciezka z `hasIssue=true`

```text
line con 0 ->  password admin123
```

Haslo konsoli jest slabe i przechowywane jawnie. Ten problem nalezy laczyc
z problemem wylaczonego `service password-encryption`, a nie liczyc jako
niezalezny blad bezpieczenstwa.

## Sciezki pozostajace jako `false`

Ponizsze sciezki nie zawieraja bledow same w sobie:

```text
interface GigabitEthernet0/1 ->  ip access-group 110 in
line con 0 ->  login
```

Zastosowanie ACL do interfejsu jest poprawne, a `login` konsoli jest poprawne,
poniewaz w bloku konsoli istnieje haslo. Problemem sa reguly ACL, hasla oraz
brak ograniczen dostepu VTY.

## Podsumowanie

| Liczba bledow logicznych | Liczba sciezek z `hasIssue=true` |
|---:|---:|
| 4 | 7 |

Sciezki dotyczace adresow IP, `GigabitEthernet0/2`, `Vlan1` oraz nieuzywanego
AUX powinny pozostac jako `false`. AUX warto wylaczyc przez `no exec`, aby nie
wprowadzac dodatkowego problemu bezpieczenstwa.
