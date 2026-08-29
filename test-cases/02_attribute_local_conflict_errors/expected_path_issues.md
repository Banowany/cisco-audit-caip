# Oczekiwane bledne sciezki

Dokument opisuje referencyjne wartosci `hasIssue` dla scenariusza
`02_attribute_local_conflict_errors`.

Etykiety odnosza sie do docelowej konfiguracji po zmianie reguly NAT tak,
aby nie wskazywala na wylaczony `GigabitEthernet0/2`:

```text
ip nat inside source list 1 interface GigabitEthernet0/1 overload
```

Sciezki nie wymienione w tym dokumencie powinny otrzymac `hasIssue=false`.

## Problem 1: OSPF obejmuje siec wylaczonego interfejsu

### Sciezka z `hasIssue=true`

```text
router ospf 1 ->  network 192.168.20.0 0.0.0.255 area 0
```

Regula OSPF obejmuje siec przypisana do `GigabitEthernet0/2`, ktory jest
administracyjnie wylaczony.

Ponizsze sciezki sa kontekstem tego problemu, ale nie sa bledami samych
polecen:

```text
interface GigabitEthernet0/2 ->  ip address 192.168.20.1 255.255.255.0
interface GigabitEthernet0/2 ->  shutdown
```

Polecenie `shutdown` jest poprawne dla nieuzywanego interfejsu. Problem wynika
dopiero z jego polaczenia z konfiguracja OSPF.

## Problem 2: niekompletna konfiguracja NAT

### Sciezka z `hasIssue=true`

```text
ip nat inside source list 1 interface GigabitEthernet0/1 overload
```

W konfiguracji nie ma zadnego interfejsu skonfigurowanego jako
`ip nat outside`. Regula NAT nie moze wiec dzialac poprawnie.

Ponizsza sciezka jest poprawnym elementem kontekstu i nie powinna byc
oznaczona jako osobny blad:

```text
interface GigabitEthernet0/0 ->  ip nat inside
```

## Problem 3: trasa domyslna przez wylaczony interfejs

### Sciezka z `hasIssue=true`

```text
ip route 0.0.0.0 0.0.0.0 GigabitEthernet0/2
```

Trasa domyslna wskazuje na administracyjnie wylaczony
`GigabitEthernet0/2`.

## Dodatkowe uwagi

W pliku `expected_errors.md` nalezy uzywac `GigabitEthernet0/2`, a nie
`GigabitEthernet0/3`, poniewaz konfiguracja scenariusza wykorzystuje
`GigabitEthernet0/2`.

Aktualna reguła NAT wskazujaca na `GigabitEthernet0/2` powoduje dodatkowe
powiazanie z bledem wylaczonego interfejsu. Nie nalezy jej uzywac jako
docelowej wersji scenariusza.

## Podsumowanie

| Liczba bledow logicznych | Liczba glownych sciezek z `hasIssue=true` |
|---:|---:|
| 3 | 3 |

Adresy IP, samo `shutdown`, deklaracje `ip nat inside`, `Vlan1` oraz
poprawnie skonfigurowane linie konsoli i VTY powinny pozostac oznaczone jako
`false`.
