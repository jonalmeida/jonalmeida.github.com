---
title: "Midnight Cookie & Pho Run"
date: 2026-10-30
draft: false
taxonomies:
  categories: ["runs"]
extra:
  hide_table_of_contents: true
  garmin_activity_id: 24910496943
  distance_km: 5.35
  duration: "29:28"
  pace_per_km: "5:31"
  elevation_gain_m: 35
  mermaid: true
  hr_zones:
    - { zone: 5, name: "Maximum", pct: 0.4 }
    - { zone: 4, name: "Threshold", pct: 0.4 }
    - { zone: 3, name: "Aerobic", pct: 14.3 }
    - { zone: 2, name: "Easy", pct: 54.5 }
    - { zone: 1, name: "Warm Up", pct: 30.5 }
  intervals:
    - { lap: 1, distance_km: "1.00", duration: "5:36", pace: "5:36" }
    - { lap: 2, distance_km: "0.84", duration: "4:24", pace: "5:13" }
    - { lap: 3, distance_km: "1.00", duration: "5:42", pace: "5:42" }
    - { lap: 4, distance_km: "1.00", duration: "5:42", pace: "5:42" }
    - { lap: 5, distance_km: "1.00", duration: "5:41", pace: "5:41" }
    - { lap: 6, distance_km: "0.50", duration: "2:24", pace: "4:46" }
---
Need I say more?

{{ <gallery page={page} /> }}

| Stat | Value |
|------|-------|
| Distance | 5.35 km |
| Duration | 29:28 |
| Pace | 5:31 /km |
| Elevation Gain | 35 m |

## Route

{{ <image path="/runs/maps/24910496943.svg" width={640} /> }}

## Intervals

{% <mermaid labels="mm:ss"> %}
---
config:
  xyChart:
    showDataLabel: true
    height: 400
---
xychart horizontal
    title "Pace per Interval (min/km)"
    x-axis ["1 · 1.00 km", "2 · 0.84 km", "3 · 1.00 km", "4 · 1.00 km", "5 · 1.00 km", "6 · 0.50 km"]
    y-axis "min/km" 0 --> 6
    bar [5.600, 5.220, 5.693, 5.697, 5.680, 4.770]
{% </mermaid> %}

## Heart Rate Zones

{% <mermaid> %}
xychart horizontal
    title "Time in Heart Rate Zones (%)"
    x-axis ["Zone 5 Maximum", "Zone 4 Threshold", "Zone 3 Aerobic", "Zone 2 Easy", "Zone 1 Warm Up"]
    y-axis "%" 0 --> 100
    bar [0.4, 0.4, 14.3, 54.5, 30.5]
{% </mermaid> %}
