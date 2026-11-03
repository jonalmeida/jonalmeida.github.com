---
title: "Toronto - Easy Run"
date: 2026-11-02
draft: false
taxonomies:
  categories: ["runs"]
extra:
  hide_table_of_contents: true
  garmin_activity_id: 24945924674
  distance_km: 7.17
  duration: "40:03"
  pace_per_km: "5:35"
  elevation_gain_m: 47
  mermaid: true
  hr_zones:
    - { zone: 5, name: "Maximum", pct: 0.0 }
    - { zone: 4, name: "Threshold", pct: 0.0 }
    - { zone: 3, name: "Aerobic", pct: 15.0 }
    - { zone: 2, name: "Easy", pct: 58.9 }
    - { zone: 1, name: "Warm Up", pct: 26.1 }
  intervals:
    - { lap: 1, distance_km: "1.00", duration: "5:36", pace: "5:36" }
    - { lap: 2, distance_km: "0.82", duration: "4:24", pace: "5:21" }
    - { lap: 3, distance_km: "1.00", duration: "5:36", pace: "5:36" }
    - { lap: 4, distance_km: "1.00", duration: "5:43", pace: "5:43" }
    - { lap: 5, distance_km: "1.00", duration: "5:37", pace: "5:37" }
    - { lap: 6, distance_km: "1.00", duration: "5:34", pace: "5:34" }
    - { lap: 7, distance_km: "1.00", duration: "5:44", pace: "5:44" }
    - { lap: 8, distance_km: "0.34", duration: "1:46", pace: "5:16" }
---
Long day, but excellent weather. 👌

| Stat | Value |
|------|-------|
| Distance | 7.17 km |
| Duration | 40:03 |
| Pace | 5:35 /km |
| Elevation Gain | 47 m |

## Route

{{ <image path="/runs/maps/24945924674.svg" width={640} /> }}

## Intervals

{% <mermaid labels="mm:ss"> %}
---
config:
  xyChart:
    showDataLabel: true
    height: 470
---
xychart horizontal
    title "Pace per Interval (min/km)"
    x-axis ["1 · 1.00 km", "2 · 0.82 km", "3 · 1.00 km", "4 · 1.00 km", "5 · 1.00 km", "6 · 1.00 km", "7 · 1.00 km", "8 · 0.34 km"]
    y-axis "min/km" 0 --> 6
    bar [5.608, 5.358, 5.607, 5.715, 5.609, 5.570, 5.730, 5.271]
{% </mermaid> %}

## Heart Rate Zones

{% <mermaid> %}
xychart horizontal
    title "Time in Heart Rate Zones (%)"
    x-axis ["Zone 5 Maximum", "Zone 4 Threshold", "Zone 3 Aerobic", "Zone 2 Easy", "Zone 1 Warm Up"]
    y-axis "%" 0 --> 100
    bar [0.0, 0.0, 15.0, 58.9, 26.1]
{% </mermaid> %}
