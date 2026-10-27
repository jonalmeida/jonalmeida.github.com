---
title: "Toronto - 4x1600"
date: 2026-08-20
draft: false
taxonomies:
  categories: ["runs"]
extra:
  hide_table_of_contents: true
  garmin_activity_id: 24048177886
  distance_km: 12.22
  duration: "1:00:02"
  pace_per_km: "4:55"
  elevation_gain_m: 51
  mermaid: true
  hr_zones:
    - { zone: 5, name: "Maximum", pct: 2.8 }
    - { zone: 4, name: "Threshold", pct: 22.2 }
    - { zone: 3, name: "Aerobic", pct: 41.7 }
    - { zone: 2, name: "Easy", pct: 25.0 }
    - { zone: 1, name: "Warm Up", pct: 8.3 }
  intervals:
    - { lap: 1, distance_km: "1.00", duration: "5:30", pace: "5:30" }
    - { lap: 2, distance_km: "1.61", duration: "6:42", pace: "4:10" }
    - { lap: 3, distance_km: "0.40", duration: "3:00", pace: "7:30" }
---
Four by a mile, with the last one honest.

{{ <gallery page={page} /> }}

| Stat | Value |
|------|-------|
| Distance | 12.22 km |
| Duration | 1:00:02 |
| Pace | 4:55 /km |
| Elevation Gain | 51 m |

## Route

{{ <image path="/runs/maps/24048177886.svg" width={640} /> }}

## Intervals

{% <mermaid labels="mm:ss"> %}
---
config:
  xyChart:
    showDataLabel: true
    height: 295
---
xychart horizontal
    title "Pace per Interval (min/km)"
    x-axis ["1 · 1.00 km", "2 · 1.61 km", "3 · 0.40 km"]
    y-axis "min/km" 0 --> 8
    bar [5.500, 4.163, 7.500]
{% </mermaid> %}

## Heart Rate Zones

{% <mermaid> %}
xychart horizontal
    title "Time in Heart Rate Zones (%)"
    x-axis ["Zone 5 Maximum", "Zone 4 Threshold", "Zone 3 Aerobic", "Zone 2 Easy", "Zone 1 Warm Up"]
    y-axis "%" 0 --> 100
    bar [2.8, 22.2, 41.7, 25.0, 8.3]
{% </mermaid> %}
