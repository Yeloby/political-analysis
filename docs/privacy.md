# Personvern og nettverk i dagens Samfunnsdata

Spørsmål skrevet i GUI tolkes lokalt med programmets parser. De sendes ikke til
en språkmodell. Utvalgte dataforespørsler går til dataleverandørene når de ikke
finnes i lokal cache. Programmet har en eksplisitt `--cache-only`-modus som
forbyr alle nettverksforespørsler. **CLI-kommandoen `search` sender søketeksten
til SSB bare når programmet er i online-modus og ingen lokal cache gir treff.**
Det er derfor ikke riktig at alle spørsmål alltid forblir lokale.

## Hva sendes?

- SSB: søketekst ved CLI-søk; kommunenavn slås opp lokalt i en hentet kodeliste.
  Befolkningskallet sender kommunekode, tabell 07459, måltall Personer1,
  aggregeringsvalg og alle år. `--since`/årsvalget filtreres lokalt.
- NAV: programmet laster en CSV-fil; kommunen filtreres lokalt.
- Valgdirektoratet: år og geografisk område inngår i API-kall; parti filtreres lokalt.
- FHI (Python/API): tabell og valgte dimensjonskoder sendes til FHI.
  FHI er ikke integrert i GUI-spørsmålene.

Mottakeren kan se offentlig IP-adresse (eller en proxy/VPN-adresse), tidspunkt,
forespørsel og HTTP-headere. HTTPS gjør ikke forespørselen usynlig for mottakeren.
HTTP-klienten bruker normalt sin bibliotekidentifikasjon som User-Agent.
HTTPX kan arve proxyinnstillinger fra miljøet. Programmet har ingen egen
VPN-funksjon eller garanti for å følge GNOMEs proxyoppsett.

Det er ikke implementert telemetri, skytjeneste for spørsmålsanalyse eller en
lagret spørsmålslogg i applikasjonen. Dette er en beskrivelse av prosjektkoden,
ikke en sikkerhetsrevisjon av alle avhengigheter og operativsystemet.

## Lokal lagring og deling

Cache lagres under plattformens brukerdatamappe, normalt
`~/.local/share/samfunnsdata/cache` på Linux (XDG-konfigurasjon kan endre dette).
JSON-/CSV-cache og valgte eksporter er ikke kryptert av programmet. Innhold og
forespørselsparametre kan avsløre hvilke utvalg som er undersøkt. En hashet
cachefilnøkkel er ikke kryptering eller en innholdshash.

Navnemigreringen kan ha kopiert den eldre `political-analysis`-datamappen og
beholdt originalen som sikkerhetskopi. CSV, PNG og datakvitteringer ligger der du
valgte å eksportere dem. CLI-argumenter kan også ligge i terminalens historikk.

Befolkningskvitteringen inkluderer forespurt kommunenavn, kommunekode, år,
kildeobservasjoner, status, beregninger, kildemetadata og brukstidspunkt. Den
inneholder ikke GUI-spørsmålet, maskinens lokale cachebane eller autentiseringsdata.
Vurder dette innholdet før deling. Ukjent hentetid/cachestatus er tydelig null;
kvitteringen er ikke et signert bevis på kildens originalrespons.

Det finnes foreløpig ingen knapp for å tømme cache. Lukk programmet før eventuell
manuell sletting av cachemappen. Dette sletter ikke eksporter, eldre sikkerhetskopier
eller terminalhistorikk. Cachen kan fylles på igjen ved senere forespørsler.

`--cache-only` og GUI-valg for «Kun lokal cache» hindrer alle nettverkskall; de
forbyr kun lokal cache og kaster en tydelig feil ved cachebom. Dette er en
nettverksgrense, ikke anonymitetsgaranti. Cachebruk er ikke et løfte om anonymitet
eller fullstendig frakoblet drift. Avbryt stopper visning av foreldede resultater,
men et pågående kildekall kan fortsatt fullføres.

## Begrensninger

Programmet har en liten, eksplisitt nettverks- og personvernpolicy for de
støttede kildene, men den beskytter ikke mot en valgt nettverksforbindelse, en
proxy, eller andre OS-/miljøregler. HTTPS skjuler ikke mot manglende godkjenning
av kildens vertsnavn eller mot den faktiske publikumstrafikken på nettverket.
