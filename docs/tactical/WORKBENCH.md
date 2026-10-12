# Local tactical research workbench

## Current stage

Five sport-specific source/parser views are implemented, with separate mechanics
companions. Numerical display is a separate, fail-closed layer: only independently
reviewed final aggregate results can open it. Development fitting alone does not
unlock those views. See `MODEL_VIEWS.md` for the full-local and separately reviewed
aggregate-snapshot contracts. All new work is outside the preserved four-sport
model packages. The completed distribution includes seven independently reviewed
aggregate snapshots; these are usable without raw data or trained weights.

## Start

From the project root. A clean distribution opens the reviewed numerical
snapshots without source summaries; descriptive views become available only after
the separate local source/parser workflow:

```sh
python -m experiments.tactical.workbench index
python -m experiments.tactical.workbench serve --port 8765
```

Open `http://127.0.0.1:8765`. Stop with Ctrl-C. Python's standard library supplies
the server. The app has no external JavaScript/CDN, account, telemetry, automatic
refresh or hidden acquisition. It binds only to IPv4 loopback and rejects foreign
Host/Origin and cross-site requests. It is not an internet-facing production server
and should not be placed behind a public tunnel or reverse proxy.

The explicit `index` command records byte hashes of approved-path aggregate
summaries. It is an integrity aid, not independent validation or a license grant.
Opening a view refuses changed/malformed artifacts, arbitrary filesystem paths and
unapproved predictive phases. Re-index only after reviewing intentional generator
changes. An absent report gives a clear unavailable state, never synthetic results.

## Interpret a view

- Observation contract: the actual unit, population, physical stage and measurement
- Conditional-count charts: unsmoothed development-sample descriptions, with support
- Geometry: source coordinates, units and a deterministic development-only sample
- Outcome overlay: explicitly later observed outcome, not a model input
- Source quality: missingness, quarantines and same-source consistency limitations
- Mechanics companion: a distinct population and target, never silently pooled
- Source/evidence: required credits and detailed research explanations

Source restrictions still apply locally and when sharing. StatsBomb views use the
verified source-supplied logo; the server does not fetch it online. All tactical
summaries and row derivatives remain ignored until a source-specific release
review. Laboratory views expose only aggregate deidentified information.

## Checks and known environment limitation

Offline unit tests cover the five-sport catalog, report integrity, strict summary
contracts, allowed routes, loopback binding, read-only behavior and security headers.
The optional JS DOM test exercises real aggregate-context selectors and document
views without a network browser. Its development dependency is isolated under
ignored artifacts and is not required to run the workbench.

The available execution sandbox blocked installed Chromium's process-socket setup,
including an approved escalation attempt. The separate cloud browser could not
reach the executor loopback service. Therefore a screenshot/visual-browser pass has
**not** been claimed. `scripts/qa_tactical_workbench.py` records the intended browser
smoke check for a capable local installation. Functional DOM tests are useful but
do not establish rendered layout, screen-reader behavior or browser compatibility.
Before calling the interface fully validated, run that check and inspect desktop
and narrow-screen views, keyboard navigation, plot labels and provider attribution.
