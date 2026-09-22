# Trinnvis arkitektur for Samfunnsdata

Status: forslag med et lite implementert fundament. Ingen nye datakilder eller
analyseadaptere innføres i denne milepælen.

## Dagens arkitektur og konkrete begrensninger

- SSB har egen klient, tabellsøk, kodelister og JSON-stat-konverter. Befolkning
  er en spesialisert funksjon; generisk tabellsøk gjør ikke alle tabeller til
  støttede analyser. Konverteren bevarer koder/etiketter, men ikke observasjonsstatus.
- FHI skiller generisk HTTP/JSON-stat2 fra legemiddelsemantikk. Status,
  dimensjonsmetadata, enheter og kildeproveniens følger legemiddelrammen i attrs.
- NAV leser en bestemt CSV med leverandørspesifikk tegnkoding, kolonnenavn og
  duplikatvalg. URL/årgang er statisk. Duplikatvalget bruker fillna(0) internt;
  dette er ikke en generell regel for behandling av manglende observasjoner.
- Valg har egen navigasjon gjennom områder, normalisering og eksplisitte
  årgangslister. Katalogen dekker foreløpig kommunevalg; implementert
  stortingsvalganalyse mangler en egen katalogoppføring.
- Katalogen var en statisk tuple med ordsøk. Den er ikke et inventar over alt
  som er offentlig tilgjengelig. Geografitype «municipality» verifiserer ikke
  at en bestemt kommunekode finnes i alle årganger.
- analysis.py er befolkningsspesifikk: forventer Tid-kolonner, heltall og
  ikke-null startverdi. Skal ikke brukes som universell statistikkmotor.
- Spørsmålsparseren er en samling eksplisitte regulære uttrykk. Behold den for
  eksisterende spørsmål; metadataoppdagelse skal få en egen vei.
- GUI-en inneholder datahenting, beregninger, diagrammer og eksport i samme
  vindu. Nettverksarbeid skjer synkront og kan blokkere GTK. Dette endres ikke her.
- JsonCache/FileCache hasher forespørsler og lagrer payload, men mangler TTL,
  hentetid, kildeversjon, innholds-hash i manifest og atomisk oppdatering.
- CSV-eksport velger noen resultatkolonner. Den bevarer ikke attrs eller en
  full kvittering. «Rådata» i GUI betyr utvalgte analyseobservasjoner, ikke
  nødvendigvis den originale HTTP-responsen.

## Implementert fundament

Source beskriver myndighet og offisiell nettside. Dataset beholder eksisterende
felt og har additive felt for adapterreferanse, grensesnitt, tabell-ID,
kilde-/tilgangs-URL, format, oppdatering, metode, seriebrudd og valgfri status som
offisiell statistikk. None betyr ukjent; tomt metadatafelt dokumenterer ikke
at en kilde mangler seriebrudd. Ukjent NAV-download-URL i katalogen fylles ikke
med en antatt API-adresse; eksisterende provider beholder den verifiserte fil-URL-en.

Støttestatus er eksplisitt og har sikker standard PLANNED:

- SUPPORTED: en implementert, navngitt adapter og oppgitte grensesnitt finnes.
  Det betyr bare det konkrete datasettet og funksjonens utvalg, ikke alle mulige
  spørringer eller alle data hos myndigheten. Tester kontrollerer at de registrerte
  adapterreferansene faktisk peker på funksjoner.
- DISCOVERED: metadata om et faktisk datasett er katalogisert, men ingen støttet
  analyse-/henteadapter er registrert. Ingen kjørehandling skal vises.
- PLANNED: ikke støttet. Verken tilgjengelighet eller maskinlesbarhet er bekreftet.

Katalogens adapterstreng er dokumentasjon, ikke dynamisk kodekjøring.
Importer aldri adapterstier hentet fra eksterne metadata. Fremtidig dispatch bruker
et eksplisitt, lokalt allowlist-register. Ukjente kilder krever en Source-oppføring.
Søk kan filtreres på kilde og støtte. Gjeldende data er fortsatt lokale og manuelt
vedlikeholdte. Ikke fyll katalogen med spekulative tabeller.

## Neste registry-trinn, uten provider-omskriving

1. Lag separate discovery-funksjoner rundt eksisterende SSB-/FHI-metadataendepunkter.
   Bruk namespaces provider/source/table som identitet. Oppdagede metadata får
   DISCOVERED, kilde-URL, hentetid og rå metadatasnapshot. Discovery må aldri
   overskrive lokalt verifisert adapterbinding eller oppgradere støtte automatisk.
2. Skill kuraterte støtteoppføringer fra innhentede snapshots. Start med versjonert
   JSON i egen cache; velg SQLite/FTS først når volum eller filtrering krever det.
   Lag migrering/versionering av formatet og bevar siste vellykkede snapshot ved feil.
3. Utvid dimensjonsbeskrivelsen med kode, etikett, rolle, kategorikilde og eventuelle
   hierarkier; måltall får enhet og kildebeskrivelse per kategori. Behold dagens
   enkle felt som kompatibilitetsvisning. Lag tidsdekning som strukturerte intervaller
   og eksplisitte brudd, ikke bare en tekststreng.
4. Indekser myndighet, tema, titler, beskrivelser og verifiserte kategorier. Et
   metadatasøk etter selvmord/kriminalitet skal returnere treff med støttestatus,
   eller si at lokal katalog ikke har treff. Det er ikke en påstand om at data
   ikke eksisterer. «Trondheim» krever kategori-/geografimetadata med kode og
   tidsdekning; ikke slutt dette fra et generelt kommune-felt.
5. Hold katalogoppdagelse adskilt fra analyseplanlegging. En plan validerer
   tilgjengelige dimensjoner/måltall mot kilden før spørring. Flertydige treff
   krever valg; aldri velg et legemiddel eller en statistikk på fri AI-gjetning.

Offentlige myndigheter som Stortinget, Skatteetaten, Politiet, domstolene,
Regjeringen, kommuner/fylker, Norges Bank, Brønnøysundregistrene, Kartverket,
Statens vegvesen, NVE og MET Norway er dekningsmål, ikke implementert støtte.
Verifiser offentlig tilgang, vilkår og maskinlesbarhet per datasett.
Prioritet: offisielt API, maskinlesbar fil (CSV/JSON/JSON-stat/Parquet), XLSX/XLS,
deretter andre strukturerte offisielle kilder. Ikke bruk skjør HTML-skraping når
en offisiell maskinlesbar kilde finnes.

## Minste fremtidige adapterkontrakt

Bruk tynne wrapper-funksjoner rundt fungerende providers. Første felles kontrakt
bør være konseptuelt fetch(validated_selection) -> AnalysisResult, der resultatet
har observations, receipt og en referanse til rå payload. Metadata/discovery er
separate operasjoner. Ingen felles abstrakt klasse med mange obligatoriske metoder.
Ingen eksisterende provider må bytte signatur samtidig.

- HTTP: del timeout/feil/retry-policy først når reell duplisering krever det.
- JSON-stat: trekk ut felles ordens-/kategoriavkoding først med SSB- og
  FHI-kontrakttester. Behold status og rå extension; dette er ikke gjort nå.
- REST/JSON: del transport; JSON-skjema og betydning normaliseres i provider.
- CSV: provider bestemmer encoding, skilletegn, datatyper og manglende-koder.
- XLSX: provider velger ark, overskriftsrader og enheter. Ingen generell
  «gjett regnearket»-motor; avhengigheter tilføyes først for et verifisert datasett.

En formatleser er ikke en analyseadapter og gir ikke automatisk SUPPORTED-status.
Behold kildekoder og kildeetiketter. Ikke reduser FHI-status til en universell boolsk
missing-kolonne. Eventuell normalisert status er et tillegg, med rå kode og
mappingversjon bevart. Estimat, foreløpig tall, undertrykking og seriebrudd er ulike
begreper; støtten må kunne representere flere flagg samtidig.

## Datakvittering: foreslått kontrakt, ikke ferdig implementert

En versjonert Receipt bør inneholde:

- authority, provider/source ID, dataset/table ID og tittel;
- offisiell source_url og den faktiske retrieval_url, format og kildeoppdatering;
- forespurt og faktisk dimensjonsutvalg, måltall, enhet og periode;
- fetched_at (faktisk henting), used_at (bruk i analysen), cache_hit, payload_hash
  og referanse til uendret rå payload; en cachelesing er ikke en ny kildehenting;
- raw/normalized/calculated som eksplisitte roller;
- beregningssteg med navn, versjon, input-referanser, formel, parametre og
  behandling av status/manglende verdier; ingen oppdiktet metodetekst;
- kildens definisjoner, metode, begrensninger, seriebrudd og original statusmetadata;
- valgfrie markeringer av offisiell statistikk, foreløpighet og estimater;
- bevart provider_metadata uten destruktiv normalisering.

Første wrapper kan bruke eksisterende FHI attrs. Gamle analyser merkes med
ufullstendig kvittering; ukjente felt forblir ukjente. Ikke presenter nåværende
kildetekst som en komplett kvittering. Behold metadata i AnalysisResult fremfor å
stole på at pandas attrs alltid følger alle join/concat-operasjoner.

Eksport bør senere skrive CSV + JSON-kvittering (eventuelt en samlet pakke).
Test maskinell gjenlesing og bevaring av null, flagg, koder, enheter og hash.
Sammenligninger krever forenlige måltall, enheter, definisjoner, geografi og periode;
ikke summer ATC-brukere eller bland prosent og prosentpoeng. Resultater kan si
«ikke beregnbart». Korrelasjon er ikke årsak.

## Desktop og hjelp

Implementert meny: Fil (ny analyse, CSV, avslutt), Data (lokal katalog,
datakilder, rådata, kildeinformasjon), Vis (manuelle befolkningsvalg), Hjelp
(brukerveiledning, Om). Eksport/rådata/kildeinfo følger eksisterende resultattilstand.
Ingen døde handlinger for åpne, kart eller oppdatering. Sammenligning og tidsserier
bruker eksisterende spørsmål/manuelle valg; egen Analyse-meny kommer først med
selvstendige, fungerende handlinger. Manuelle valg er skjult ved oppstart.

Hjelp lagres i help_content.json som en pakket ressurs, lastes uten nett og vises
med seksjonsnavigasjon. Teksten skiller faktisk støtte fra mål, og kildedata fra
beregning/tolkning. Om-vinduet bruker installert versjonsmetadata med lokal fallback,
prosjektets deklarerte MIT-lisens og bunnteksten «Laget av Johan Slåttavik».
Ingen ny prosjekt-URL eller opphavsrettsinformasjon gjettes.

Neste GUI-migrering: flytt først datahenting til arbeidstråd med GTK-oppdatering via
hovedløkken, kansellering og bundet resultatidentitet. Flytt deretter én eksisterende
analyse om gangen til AnalysisResult. Ikke kombiner dette med provider-omskriving.

## Anbefalte neste tre data-/provider-milepæler

1. SSB metadata discovery: paginering, dimensjonskatalog og verifiserte kategorier,
   alle nye tabeller DISCOVERED. Ingen automatisk løfte om analyserbarhet.
2. FHI discovery og første kvitteringswrapper: kilder/tabeller, status/enheter og
   metadata-snapshots; bruk eksisterende lmr/825 som ende-til-ende referanse.
3. NAV dataforvaltning: dokumentert oppdateringsvei for eksisterende CSV, versjonert
   cache/hentetid og synlige seriebrudd; avklar aktuell offisiell distribusjon før
   eventuell støtte for flere filer eller et nytt format.

Dette prioriterer bredde gjennom metadata og pålitelighet før flere enkeltkilder.
