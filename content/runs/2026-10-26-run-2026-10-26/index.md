---
title: "Halloween Decor Exploration"
date: 2026-10-26
draft: false
taxonomies:
  categories: ["runs"]
extra:
  hide_table_of_contents: true
  garmin_activity_id: 24863492365
  distance_km: 5.72
  duration: "33:07"
  pace_per_km: "5:47"
  elevation_gain_m: 67
  mermaid: true
  hr_zones:
    - { zone: 5, name: "Maximum", pct: 0.0 }
    - { zone: 4, name: "Threshold", pct: 2.3 }
    - { zone: 3, name: "Aerobic", pct: 12.1 }
    - { zone: 2, name: "Easy", pct: 30.9 }
    - { zone: 1, name: "Warm Up", pct: 54.7 }
  intervals:
    - { lap: 1, distance_km: "1.00", duration: "5:50", pace: "5:50" }
    - { lap: 2, distance_km: "0.52", duration: "4:10", pace: "8:02" }
    - { lap: 3, distance_km: "1.00", duration: "5:56", pace: "5:56" }
    - { lap: 4, distance_km: "1.00", duration: "5:26", pace: "5:26" }
    - { lap: 5, distance_km: "1.00", duration: "5:25", pace: "5:25" }
    - { lap: 6, distance_km: "1.00", duration: "5:16", pace: "5:16" }
    - { lap: 7, distance_km: "0.21", duration: "1:04", pace: "5:11" }
---
Marked a bunch of locations that I wanted to visit - was not disappointed.

{{ <gallery page={page} /> }}

| Stat | Value |
|------|-------|
| Distance | 5.72 km |
| Duration | 33:07 |
| Pace | 5:47 /km |
| Elevation Gain | 67 m |

## Route

{{ <image path="/runs/maps/24863492365.svg" width={640} /> }}

## Intervals

{% <mermaid labels="mm:ss"> %}
---
config:
  xyChart:
    showDataLabel: true
---
xychart
    title "Pace per Interval (min/km)"
    x-axis ["Lap 1 · 1.00 km", "Lap 2 · 0.52 km", "Lap 3 · 1.00 km", "Lap 4 · 1.00 km", "Lap 5 · 1.00 km", "Lap 6 · 1.00 km", "Lap 7 · 0.21 km"]
    y-axis "min/km" 0 --> 9
    bar [5.835, 8.034, 5.931, 5.433, 5.420, 5.267, 5.186]
{% </mermaid> %}

## Heart Rate Zones

{% <mermaid> %}
xychart horizontal
    title "Time in Heart Rate Zones (%)"
    x-axis ["Zone 5 Maximum", "Zone 4 Threshold", "Zone 3 Aerobic", "Zone 2 Easy", "Zone 1 Warm Up"]
    y-axis "%" 0 --> 100
    bar [0.0, 2.3, 12.1, 30.9, 54.7]
{% </mermaid> %}
