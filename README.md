# Samfunnsdata

**Offentlige data. Etterprøvbare svar.**

Samfunnsdata er et gratis og åpent Linux-program for utvalgte analyser av
norske offentlige data. Programmet har et GTK-grensesnitt, støtte for bestemte
spørsmålsformuleringer, diagrammer, CSV-eksport og lokal mellomlagring.

## Implementert

- SSB: befolkningsutvikling i kommuner og sammenligning mellom kommuner, med
  strukturert resultat og datakvittering som kan vises og eksporteres som JSON.
- Valgdirektoratet: partihistorikk og sammenligninger for stortingsvalg og
  kommunevalg, innenfor årgangene leverandøren støtter i programmet.
- NAV: registrerte helt ledige etter kommune og måned.
- Datasettkatalog med søk og informasjon om kilder, måltall og begrensninger.
- FHI Open API: generiske tabellforespørsler og JSON-stat2 til pandas, med
  kategorikoder, etiketter, verdier, status og metadata bevart.
- FHI legemidler (`lmr`, tabell `825`): ATC-oppslag og kandidatsøk, historikk
  etter kjønn, alder og måltall, samt siste observasjon med eksplisitt status.
  Denne støtten finnes på Python/API-nivå; den er ikke integrert i GUI,
  naturlige språkspørsmål eller egne CLI-kommandoer.

## Planlagt og langsiktig mål

Målet er å kunne finne relevante åpne norske data fra vanlige spørsmål og
vise etterprøvbare svar med kilde, metode, rådata og eksportmuligheter.
Programmet håndterer foreløpig bare de implementerte analysene og støttede
spørsmålsformuleringene. Legemiddelspørsmål i naturlig språk, GUI-integrasjon
for legemidler og flere datakilder er videre arbeid.

## Bruk

Installer prosjektet og skrivebordsintegrasjonen med:

```bash
./install.sh
```

Kommandolinjeverktøyet heter `samfunnsdata`. Se tilgjengelige kommandoer med
`samfunnsdata --help`. Det grafiske grensesnittet startes med
`samfunnsdata-gui` eller fra programmenyen.

## Navigasjon og dokumentasjon

Fil-menyen gir ny analyse og CSV-eksport. Data-menyen viser den lokale
katalogen, datakilder og rådata/kildeinformasjon for analyseresultatet.
Vis-menyen åpner manuelle befolkningsvalg. Hjelp-menyen inneholder en
frakoblet brukerveiledning og Om Samfunnsdata.

Katalogen skiller mellom støttet, katalogisert og planlagt, og viser hvilke
grensesnitt som er implementert. Den er ikke en komplett oversikt over norske
offentlige data. Se [arkitektur og migreringsplan](docs/architecture.md) for
videre arbeid med oppdagelse, adaptere og datakvitteringer.

## Datakvittering og personvern

Befolkningsresultater har «Vis datakvittering» og separat JSON-eksport i GUI.
CLI `population` og `compare` støtter `--receipt PATH`. CSV-formatet beholdes.
Ukjent opprinnelig hentetid vises som ukjent, også for eldre cacheposter.
Se [befolkningsresultater](docs/population-results.md).

GUI-spørsmål tolkes lokalt; datautvalg sendes til kildene ved behov. CLI `search`
sender søketeksten til SSB ved cachebom. Ingen telemetri er implementert.
Cache og eksporter lagres lokalt uten kryptering fra programmet. Det finnes
ingen cache-only-modus. Se [personvern og nettverk](docs/privacy.md).
