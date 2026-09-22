# Milestone B: GTK background work

## Blocking paths before implementation (milestone A)

GTK `clicked` / Entry `activate` → `on_question` → synchronous handler:

- Population/manual form: `on_analyze` → `municipality_population` (SSB metadata,
  cache/network and JSON-stat decoding) → filtering and `summarize_series` →
  optional second municipality → `population_figure` → `_display_chart`.
- NAV: `on_unemployment_question` → `municipality_unemployment_since`
  (download/cache, CSV parsing and selection) → presentation/date preparation →
  pyplot → `_display_chart`.
- Parliamentary and municipal elections: `on_election_question` /
  `on_municipal_election_question` → corresponding party-history provider
  (cache/network and historical selection) → endpoint summary → pyplot or
  `election_figure` → `_display_chart`.
- Both election comparisons: comparison handler → two sequential party-history
  calls → `align_election_series` → summary → pyplot → `_display_chart`.
- `_display_chart`: PNG render/write, pixel loading and widget update all on GTK.
- `on_show_raw`: row iteration and formatting before constructing the text view.
- `on_export_finished`: copying/renaming/concatenating frames and writing CSV.

All of those callbacks occupied the main loop until completion. Question parsing
and form validation are local, short operations and can remain on GTK.

## Bounded execution

A window owns one `GuiJobs` controller: at most two submitted/running calls and
one replaceable pending request. Additional requests replace that pending slot;
they do not accumulate in the executor queue. Only GTK schedules/delivers jobs.
NAV fetch+parse calls additionally share a process-wide lock: its existing raw
CSV cache writes in place, so concurrent GUI NAV calls must not read during a
write. This does not change the provider or cache implementation.
Workers return GUI-local presentation data, never manipulate widgets. Completion
is delivered through `GLib.idle_add` and checked against the current generation.
Successes, errors and chart data from older generations are discarded.

Cancellation/new requests/reset invalidate generations and set cooperative tokens.
Checkpoints surround provider steps and rendering. Synchronous HTTP already in
progress is not aborted; existing provider timeouts remain in force. A close
invalidates everything and shuts down without waiting; late callbacks touch no
widgets. Python may still wait for an in-flight worker at process exit.

All GUI pyplot work is guarded by one process-wide lock, including creation,
layout, PNG rendering and close. Unique temporary PNG files are removed before
results are delivered. GTK uses a texture and `Picture.set_paintable`.

Raw-data formatting and CSV preparation/writing also use this controller with a
snapshot of the selected result. File dialogs stay on GTK. Cancellation cannot
undo a CSV write that has already started.
