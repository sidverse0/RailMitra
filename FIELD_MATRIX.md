# Field Matrix

Exhaustive, field-by-field accounting of what each original project
extracted vs. what the final unified API returns. "Python" and "JS" columns
describe the ORIGINAL projects' own output only — not the final API.

## Train info (`train_base`) — `/api/train/{no}`, `/api/trains`, `/api/trains/date`

| Field | Python (`TrainsToJson`) | JS `CheckTrain` (single train) | JS `BetweenStation` (train list) | Final Unified API |
|---|---|---|---|---|
| train_no | ✅ | ✅ | ✅ | ✅ |
| train_name | ✅ | ✅ | ✅ | ✅ |
| source_stn_name | ✅ | ❌ | ✅ | ✅ |
| source_stn_code | ✅ | ❌ | ✅ | ✅ |
| dstn_stn_name | ✅ | ❌ | ✅ | ✅ |
| dstn_stn_code | ✅ | ❌ | ✅ | ✅ |
| from_stn_name | ✅ | ✅ | ✅ | ✅ |
| from_stn_code | ✅ | ✅ | ✅ | ✅ |
| to_stn_name | ✅ | ✅ | ✅ | ✅ |
| to_stn_code | ✅ | ✅ | ✅ | ✅ |
| from_time | ✅ | ✅ | ✅ | ✅ |
| to_time | ✅ | ✅ | ✅ | ✅ |
| travel_time | ✅ | ✅ | ✅ | ✅ |
| running_days | ✅ | ✅ | ✅ | ✅ |
| source_depart | ✅ | ❌ | ❌ | ✅ |
| dstn_reach | ✅ | ❌ | ❌ | ✅ |
| type | ✅ | ✅ | ❌ | ✅ |
| train_id | ✅ | ✅ | ❌ | ✅ |
| distance_from_to | ✅ | ✅ | ❌ | ✅ |
| average_speed | ✅ | ✅ | ❌ | ✅ |
| notif_coach | ✅ | ❌ | ❌ | ✅ |
| coach_types (1A/2A/3A/CC/SL/2S/GN) | ✅ | ❌ | ❌ | ✅ |
| train_type (heuristic) | ✅ | ❌ | ❌ | ✅ |
| region (heuristic) | ✅ | ❌ | ❌ | ✅ |
| rake_share (heuristic) | ✅ | ❌ | ❌ | ✅ |
| coach_arrangement (heuristic) | ✅ | ❌ | ❌ | ✅ |

**Note:** all 4 "heuristic" fields (`train_type`, `region`, `rake_share`,
`coach_arrangement`) use the *exact* pattern-matching heuristic from the
original Python `Prettify._extract` — there is no reliable fixed field
index for these in the upstream response, so this heuristic (imperfect, but
the only known mapping) is preserved as-is and degrades to omitting the
field rather than guessing wrong.

## Route / station info — `/api/route/{no}`

| Field | Python (`StationToJson`) | JS (`GetRoute`) | Final Unified API |
|---|---|---|---|
| index | ✅ | ❌ | ✅ |
| code | ✅ (`code`) | ✅ (`source_stn_code`) | ✅ (`code`) |
| name | ✅ (`name`) | ✅ (`source_stn_name`) | ✅ (`name`) |
| arrival | ✅ (`arrival`) | ✅ (`arrive`) | ✅ (`arrival`) |
| depart | ✅ | ✅ | ✅ |
| halt | ✅ | ❌ | ✅ |
| distance_from_source | ✅ | ✅ (`distance`) | ✅ (`distance_from_source`) |
| day | ✅ | ✅ | ✅ |
| platform | ✅ | ❌ | ✅ |
| zone | ✅ (index 10) | ⚠️ (index 9 after empty-field filtering — likely shifted/buggy) | ✅ (Python's index adopted as canonical; see README discrepancy #2) |
| division | ✅ | ❌ | ✅ |
| lat | ✅ | ❌ | ✅ |
| lng | ✅ | ❌ | ✅ |

## Fare — `/api/fare` (Python-only feature)

| Field | Python (`FareToJson`) | Final Unified API |
|---|---|---|
| class name (row key) | ✅ | ✅ |
| fare type (column key, e.g. General/Tatkal/Premium) | ✅ | ✅ |
| fare amount (or `-` if unavailable) | ✅ | ✅ |

## Availability — `/api/availability` (Python-only feature)

| Field | Python (`AvailToJson`) | Final Unified API |
|---|---|---|
| train_no | ✅ | ✅ |
| from_code | ✅ | ✅ |
| to_code | ✅ | ✅ |
| class | ✅ | ✅ |
| date | ✅ | ✅ |
| status | ✅ | ✅ |
| "No Results Found" case | ⚠️ implicit / unhandled | ✅ explicit `{"status": "No Results Found"}` |

## Train running status — `/api/status` (Python-only feature)

| Field | Python (`getStatus`) | Final Unified API |
|---|---|---|
| Raw upstream JSON (train position/delay fields as returned by tripmgt.com) | ✅ passthrough, unvalidated | ✅ passthrough, validated as real JSON (raises `MALFORMED_UPSTREAM_RESPONSE` otherwise) |

## Station live — `/api/station-live/{code}` (JS-only feature)

| Field | JS (`LiveStation`) | Final Unified API |
|---|---|---|
| train_no | ✅ | ✅ |
| train_name | ✅ | ✅ |
| source_stn_name | ✅ | ✅ |
| dstn_stn_name | ✅ | ✅ |
| time_at | ✅ | ✅ |
| detail (delay/status text) | ✅ | ✅ |

## PNR — `/api/pnr/{pnr}`

| Field | Python (`getPNR`, indianrail.gov.in) | JS (`PnrStatus`, ConfirmTkt) | Final Unified API |
|---|---|---|---|
| Full PNR payload (passenger list, chart status, train info, etc.) | ✅ raw JSON passthrough from indianrail.gov.in | ✅ raw embedded JSON passthrough from ConfirmTkt | ✅ both sources preserved, selectable via `?source=`; each returns its own upstream's native field set (not merged, since they're independent sources — see README) |

## Error fields (new in the unified API — not present as structured data in either original)

| Field | Final Unified API |
|---|---|
| `success` (boolean) | ✅ |
| `timestamp` (unix seconds) | ✅ |
| `error.code` (machine-readable) | ✅ |
| `error.message` (human-readable) | ✅ |
