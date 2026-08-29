# Etykietowanie blednych sciezek konfiguracji

Dokument opisuje rekomendowane etykiety dla sciezek konfiguracji w trzech
scenariuszach badawczych. Ustalenia opieraja sie na plikach `router.conf`,
opisach scenariuszy oraz zalozeniach metody opisanych w pracy. Nie nalezy
traktowac wygenerowanych wynikow audytu jako zrodla etykiet referencyjnych.

## Zasada etykietowania

Etykieta `true` oznacza, ze sciezka jest bezposrednio zwiazana z bledem po
uwzglednieniu calej konfiguracji. Sciezka uzyta wylacznie jako kontekst
pozostaje `false`, jezeli samo polecenie jest poprawne.

Jeden blad logiczny moze dotyczyc kilku sciezek. W takim przypadku mozna
oznaczyc wszystkie sciezki nalezace do wadliwej konstrukcji jako `true`, ale
podczas podsumowania wynikow trzeba liczyc je jako jeden blad logiczny.

Przyklad: piec sciezek skladajacych sie na nieuzywana ACL oznacza piec
blednych rekordow na poziomie sciezek, ale tylko jeden blad konfiguracji.

## Scenariusz 1: structural and reference errors

### Sciezki oznaczane jako `true`

```text
interface GigabitEthernet0/1 ->  ip access-group 100 in
```

Interfejs odwoluje sie do ACL 100, ktora nie jest zdefiniowana.

```text
ip nat inside source list NAT_TRAFFIC interface GigabitEthernet0/0 overload
```

Regula NAT odwoluje sie do nieistniejacej ACL `NAT_TRAFFIC`.

Nastepujace sciezki oznacz jako `true` jako jedna grupe reprezentujaca
nieuzywana ACL 150:

```text
access-list 150 remark Legacy Internet Edge Filter
access-list 150 deny tcp any any eq telnet
access-list 150 deny tcp any any eq ftp
access-list 150 deny tcp any any eq www
access-list 150 permit ip any any
```

ACL 150 jest zdefiniowana, ale nie jest uzywana przez interfejs, NAT, VTY ani
inna usluge.

### Sciezki pozostawiane jako `false`

Adresy IP interfejsow, `ip nat outside`, `ip nat inside`, wylaczony
`GigabitEthernet0/2` oraz domyslna konfiguracja `Vlan1` nie sa bledami tego
scenariusza.

W aktualnym pliku wystepuje dodatkowo:

```text
line vty 0 4 ->  login
```

`login` bez hasla ani innej metody uwierzytelniania jest bledem funkcjonalnym,
ale jest to niezamierzony problem dodatkowy. Nalezy go usunac przed badaniem,
a nie dodawac do docelowego scenariusza strukturalnego.

Docelowo scenariusz zawiera 3 bledy logiczne i 7 blednych sciezek.

## Scenariusz 2: attribute and local conflict errors

Przed badaniem nalezy zmienic regule NAT, aby nie wskazywala na wylaczony
`GigabitEthernet0/2`:

```text
no ip nat inside source list 1 interface GigabitEthernet0/2 overload
ip nat inside source list 1 interface GigabitEthernet0/1 overload
```

Nalezy takze usunac `ip nat inside` z `GigabitEthernet0/1`. Wtedy
`GigabitEthernet0/0` pozostaje interfejsem inside, a regule NAT brakuje
interfejsu `ip nat outside`, co pozostawia tylko zamierzony blad NAT.

### Sciezki oznaczane jako `true`

```text
router ospf 1 ->  network 192.168.20.0 0.0.0.255 area 0
```

OSPF obejmuje siec przypisana do administracyjnie wylaczonego
`GigabitEthernet0/2`.

```text
ip nat inside source list 1 interface GigabitEthernet0/1 overload
```

W konfiguracji nie ma zadnego interfejsu `ip nat outside`, wiec konfiguracja
NAT jest niekompletna.

```text
ip route 0.0.0.0 0.0.0.0 GigabitEthernet0/2
```

Trasa domyslna wskazuje na administracyjnie wylaczony interfejs.

### Sciezki kontekstowe

Ponizsze sciezki sa potrzebne do potwierdzenia konfliktu, ale same w sobie
nie sa blednymi poleceniami:

```text
interface GigabitEthernet0/2 ->  ip address 192.168.20.1 255.255.255.0
interface GigabitEthernet0/2 ->  shutdown
interface GigabitEthernet0/0 ->  ip nat inside
```

`shutdown` jest poprawnym poleceniem dla nieuzywanego interfejsu. Staje sie
problemem dopiero w polaczeniu z OSPF i trasa domyslna. Analogicznie
`ip nat inside` jest poprawne w kompletnej konfiguracji NAT; problemem jest
brak `ip nat outside`.

W aktualnym pliku dodatkowo wystepuje:

```text
line vty 0 4 ->  login
```

Jest to niezamierzony blad funkcjonalny wynikajacy z braku hasla VTY i nalezy
go usunac przed badaniem.

W `expected_errors.md` nalezy uzywac `GigabitEthernet0/2`, a nie
`GigabitEthernet0/3`, poniewaz aktualna konfiguracja wykorzystuje
`GigabitEthernet0/2`.

Docelowo scenariusz zawiera 3 bledy logiczne i 3 glowne bledne sciezki.

## Scenariusz 3: security policy and control logic errors

### Sciezki oznaczane jako `true`

```text
no service password-encryption
```

W konfiguracji wystepuja hasla konsoli i VTY, a ich szyfrowanie jest
wylaczone. Hasla sa przechowywane jawnie.

```text
enable password cisco
```

Uzywany jest starszy i slabszy mechanizm `enable password`, dodatkowo
z latwym do odgadniecia haslem.

Obie ponizsze sciezki oznacz jako jedna grupe reprezentujaca shadowing ACL:

```text
access-list 110 permit ip any any
access-list 110 deny tcp any any eq 22
```

Pierwsza regula dopasowuje caly ruch, dlatego pozniejsza regula blokujaca SSH
nie zostanie wykonana. Samo zastosowanie ACL do interfejsu nie jest bledem.

```text
line con 0 ->  password admin123
```

Haslo konsoli jest slabe i przechowywane jawnie.

Obie ponizsze sciezki oznacz jako jedna grupe reprezentujaca niezabezpieczony
dostep VTY:

```text
line vty 0 4 ->  password telnet123
line vty 0 4 ->  login
```

Blok VTY uzywa slabej jawnej autentykacji i nie ogranicza protokolu ani
zrodel dostepu przez `transport input ssh` oraz `access-class`.

`login` w bloku VTY nie jest bledem skladniowym. Jest oznaczany jako element
wadliwej grupy VTY, poniewaz caly blok nie ma wymaganych ograniczen dostepu.

### Sciezki pozostawiane jako `false`

```text
interface GigabitEthernet0/1 ->  ip access-group 110 in
line con 0 ->  login
```

Zastosowanie ACL do interfejsu jest poprawne, a `login` konsoli jest poprawne,
poniewaz w tym bloku istnieje haslo. Problemem jest haslo, jego jawne
przechowywanie oraz brak ograniczen VTY, a nie samo polecenie `login`.

Adresy IP, wylaczony `GigabitEthernet0/2`, domyslna konfiguracja `Vlan1` oraz
nieuzywany AUX nie naleza do zamierzonych bledow tego scenariusza. AUX warto
wylaczyc przez `no exec`, aby nie wprowadzac dodatkowego problemu
bezpieczenstwa.

Nie nalezy dodawac w tym scenariuszu `service password-encryption`,
`enable secret`, `transport input ssh` ani `access-class`, poniewaz usuneloby
to zamierzone bledy.

Docelowo scenariusz zawiera 4 bledy logiczne i 7 blednych sciezek.

## Zasady podsumowania wynikow

Nie nalezy utozsamiac liczby rekordow `hasIssue=true` z liczba bledow
konfiguracji:

| Scenariusz | Bledy logiczne | Bledne sciezki |
|---|---:|---:|
| 1 | 3 | 7 |
| 2 | 3 | 3 |
| 3 | 4 | 7 |

Shadowing ACL 110, nieuzywana ACL 150 oraz niezabezpieczony blok VTY sa
przykladami bledow logicznych reprezentowanych przez wiecej niz jedna
sciezke.
