# Benchmark Reference for BLS Validation

`benchmark_reference.csv` contains **NASA Exoplanet Archive validated ephemerides** for 12 well-known exoplanet systems. Use this file in Phase 4 to verify that BLS recovers known periods within tolerance.

## Regenerate

```bash
make build-benchmark
# or: PYTHONPATH=src python scripts/build_benchmark_reference.py
```

## Schema

| Column | Unit | BLS comparison |
|--------|------|----------------|
| `tic_id` | — | Target to download/process |
| `planet_name` | — | Display label |
| `host_star` | — | Host name from archive |
| `period_days` | days | Compare to BLS best period |
| `transit_depth_fraction` | flux fraction | `pl_trandep / 100` from NASA |
| `duration_hours` | hours | Compare to BLS duration (×1/24 for days) |
| `source_catalog` | — | Always `NASA Exoplanet Archive pscomppars` |
| `validation_status` | — | `validated` or `tic_corrected` |
| `validation_notes` | — | Archive name overrides, TIC corrections |

## Recommended BLS Pass Criteria

| Parameter | Pass threshold |
|-----------|----------------|
| Period | `\|P_bls - P_ref\| / P_ref < 5%` |
| Duration | `\|T_bls - T_ref\| / T_ref < 20%` (optional) |

## Validation Notes (2026-06-25)

Nine TIC IDs in the original curated list were **incorrect** and have been corrected against `pscomppars`:

| Planet | Old TIC | Correct TIC |
|--------|---------|-------------|
| TOI-700 b | 25155310 | **150428135** |
| LHS 3844 b | 441420236 | **410153553** |
| HD 21749 b | 122641481 | **279741379** |
| GJ 357 b | 349577333 | **413248763** |
| WASP-12 b | 307210830 | **86396382** |
| L 98-59 b | 229093918 | **307210830** |
| TOI-1338 b | 260728333 | **260128333** |
| KELT-9 b | 166620049 | **16740101** |
| NGTS-2 b | 41472818 | **125739286** |

**Name overrides:** NASA uses `pi Men c` (lowercase) and `HD 21749 c` for the inner transiting planet listed as HD 21749 b in our benchmark set.

## Units

- NASA `pl_trandep` is in **percent** → stored as `transit_depth_pct` and converted to `transit_depth_fraction` for BLS comparison
- NASA `pl_trandur` is in **hours** → stored as `duration_hours` and `duration_days`
