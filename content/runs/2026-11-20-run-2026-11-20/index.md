---
title: "Toronto - Easy Run"
date: 2026-11-20
draft: false
taxonomies:
  categories: ["runs"]
extra:
  hide_table_of_contents: true
  garmin_activity_id: 25143591222
  distance_km: 4.07
  duration: "21:33"
  pace_per_km: "5:18"
  elevation_gain_m: 26
  mermaid: true
  hr_zones:
    - { zone: 5, name: "Maximum", pct: 0.0 }
    - { zone: 4, name: "Threshold", pct: 4.6 }
    - { zone: 3, name: "Aerobic", pct: 26.4 }
    - { zone: 2, name: "Easy", pct: 48.1 }
    - { zone: 1, name: "Warm Up", pct: 20.8 }
  intervals:
    - { lap: 1, distance_km: "1.00", duration: "5:24", pace: "5:24" }
    - { lap: 2, distance_km: "0.88", duration: "4:36", pace: "5:13" }
    - { lap: 3, distance_km: "1.00", duration: "5:19", pace: "5:19" }
    - { lap: 4, distance_km: "1.00", duration: "5:17", pace: "5:17" }
    - { lap: 5, distance_km: "0.19", duration: "0:57", pace: "5:01" }
---
Got a stitch that wouldn't budge. Pivoted to french toast. 🧇

{{ <gallery page={page} /> }}

| Stat | Value |
|------|-------|
| Distance | 4.07 km |
| Duration | 21:33 |
| Pace | 5:18 /km |
| Elevation Gain | 26 m |

## Route

{{ <image path="/runs/maps/25143591222.svg" width={640} /> }}

## Intervals

{% <mermaid labels="mm:ss"> %}
---
config:
  xyChart:
    showDataLabel: true
    height: 365
---
xychart horizontal
    title "Pace per Interval (min/km)"
    x-axis ["1 · 1.00 km", "2 · 0.88 km", "3 · 1.00 km", "4 · 1.00 km", "5 · 0.19 km"]
    y-axis "min/km" 0 --> 6
    bar [5.401, 5.214, 5.320, 5.283, 5.009]
{% </mermaid> %}

## Heart Rate Zones

{% <mermaid> %}
xychart horizontal
    title "Time in Heart Rate Zones (%)"
    x-axis ["Zone 5 Maximum", "Zone 4 Threshold", "Zone 3 Aerobic", "Zone 2 Easy", "Zone 1 Warm Up"]
    y-axis "%" 0 --> 100
    bar [0.0, 4.6, 26.4, 48.1, 20.8]
{% </mermaid> %}
