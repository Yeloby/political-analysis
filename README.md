# Samfunnsdata

**Offentlige data. Etterprøvbare svar.**

Samfunnsdata er et lokalt, åpent verktøy for å finne, forstå og bruke norske
offentlige data. Det er bygget for å være tydelig om hva som faktisk er
støttet, hva som bare er katalogisert, og hva som er planlagt. Hensikten er
ikke å gjette eller å presentere et løst svar som om det var en fullstendig
offisiell analyse; hensikten er å gjøre offentlige tall mer etterprøvbare.

## Hva programmet kan brukes til

- Se befolkningsutvikling i en kommune over tid
- Sammenligne kommuner med samme mål og samme tidsfilter
- Søk i en lokal katalog over norske offentlige datasett
- Se hvilke kilder som er støttet, hvilke som bare er oppdaget, og hvilke som
  fortsatt er planlagt
- Eksportere CSV og datakvitteringer til fil, når analysen støttes

## Et konkret eksempel

```bash
samfunnsdata population Trondheim --since 2010
samfunnsdata compare Trondheim Bergen --since 2010
samfunnsdata search "befolkning"
```

Dette er ekte kommandoer i programmet. De viser hvordan Samfunnsdata bruker en
lokalt validert analyseplan for å hente og presentere et kjent, støttet
datasett uten å gjøre vilkårlige antagelser om øvrige tabeller.

## Nåværende kapabiliteter

Programmet støtter i dag et begrenset, men eksplisitt utvalg av norske
offentlige datakilder og analyser:

- SSB: kommune- og befolkningsdata, sammenligninger og datakatalog
- NAV: registrerte helt ledige, hvor det er tilgjengelig via dagens implementasjon
- Valgdirektoratet: partivalgssammenligninger i de formene programmet faktisk
  støtter
- FHI: registrerte helse- og legemiddeldata via tilgjengelige, lokale Python-API
  flyter, uten å gjøre vilkårlige analyser automatiske i GUI eller naturlig språk

Dette er ikke et generelt “alt fra alle offentlige kilder”-prosjekt. Det er et
lokalt, etterprøvbart verktøy med tydelige grenser.

## Støttet, katalogisert og planlagt

Samfunnsdata skiller tydelig mellom tre tilstander:

- Støttet: datasettet har en eksplisitt adapter og et etablerte analyseflyt i
  programmet.
- Katalogisert: metadata er oppdaget og lagret lokalt, men datasettet er ikke
  automatisk kjørbart eller semantisk støttet i Samfunnsdata.
- Planlagt: det finnes en realistisk ambisjon om å støtte det senere, men det er
  ikke implementert enda.

Den viktige regelen er enkel: oppdaget metadata kan fortelle deg at et datasett
finnes, men det kan ikke gi det kjørbar status i programmet.

## Kilder i prosjektet

Disse er ekte norske offentlige kilder som ligger i prosjektets reelle
arbeidsområde:

- Statistisk sentralbyrå (SSB): https://www.ssb.no
- NAV: https://www.nav.no
- Valgdirektoratet: https://www.valgresultat.no
- Folkehelseinstituttet (FHI): https://www.fhi.no

Prosjektet bruker disse kildene der det er implementert, og tar hensyn til hva
som faktisk er etterprøvbart i en lokal, strukturert analyse.

## Personvern og lokal prosessering

Samfunnsdata er bygget for å gjøre mest mulig lokalt. GUI og CLI tolker spørsmål
lokalt, og analysene valideres før de kjøres. Katalogoppdateringer, cache og
eksport lagres i brukerens lokale miljø, og programmet har en eksplisitt
`--cache-only`-modus som stopper nettverk uten at det lar programmet skjule
hvilke datakilder som faktisk ble brukt.

Det betyr ikke at programmet er en anonymitetstjeneste eller en fullstendig
frakoblet løsning; det betyr at overvåkning og andre beslutninger er eksplicitte
og mønsterbare. Se [docs/privacy.md](docs/privacy.md) for mer om nettverk,
lagring og lokale grenser.

## Hvordan du kommer i gang

Installer prosjektet og skrivbordsintegrasjonen med:

```bash
./install.sh
```

Deretter kan du bruke CLI-en med:

```bash
samfunnsdata --help
```

Hvis du vil starte den grafiske brukerflaten, bruk den som passer for ditt
miljø, eller start prosjektet i den lokale utviklingsoppsettet du bruker.

## Bredere ambisjon

Samfunnsdata vil gjøre det enklere å ta norske offentlige data i bruk uten å
miste kontrollen over kilde, metode og begrensning. Langsiktig mål er at
brukeren skal kunne finne relevante datasett, forstå hva som er støttet, og få
afterprøvbare svar som er tydelig knyttet til en faktisk datakilde.

Det er ikke et løfte om å støtte alle offentlige data eller å automatisere alt
fra alle myndigheter. Det er et løp mot mer forståelige, mer åpne og mer
afterprøvbare analyser innenfor et avgrenset, ryddig sett av datasett.

Se [docs/architecture.md](docs/architecture.md) for arkitekturen bak prosjektet, og
[docs/privacy.md](docs/privacy.md) for personvern og nettverksmodellen.
