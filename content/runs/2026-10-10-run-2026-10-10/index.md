---
title: "Run to Ferdi's"
date: 2026-10-10
draft: false
taxonomies:
  categories: ["runs"]
extra:
  hide_table_of_contents: true
  garmin_activity_id: 24676209113
  distance_km: 4.66
  duration: "25:07"
  pace_per_km: "5:23"
  elevation_gain_m: 17
  mermaid: true
  hr_zones:
    - { zone: 5, name: "Maximum", pct: 8.8 }
    - { zone: 4, name: "Threshold", pct: 17.7 }
    - { zone: 3, name: "Aerobic", pct: 40.8 }
    - { zone: 2, name: "Easy", pct: 22.8 }
    - { zone: 1, name: "Warm Up", pct: 9.8 }
---
No time to stretch! Lazed my way out of bed to the road to work up an appetite for a chip butty. We came here before it was cool and gained a Toronto queue.

Geary parkette is also complete.

{{ <gallery page={page} /> }}

| Stat | Value |
|------|-------|
| Distance | 4.66 km |
| Duration | 25:07 |
| Pace | 5:23 /km |
| Elevation Gain | 17 m |

## Route

{{ <image path="/runs/maps/24676209113.svg" width={640} /> }}

## Heart Rate Zones

{% <mermaid> %}
---
config:
  themeVariables:
    xyChart:
      plotColorPalette: "#555555,#FF8200,#56CC3C,#4090D4,#AAAAAA"
      backgroundColor: "transparent"
---

xychart horizontal
    title "Time in Heart Rate Zones (%)"
    x-axis ["Zone 5 Maximum", "Zone 4 Threshold", "Zone 3 Aerobic", "Zone 2 Easy", "Zone 1 Warm Up"]
    y-axis "%" 2 --> 100
    bar [8.8, 0.0, 0.0, 0.0, 0.0]
    bar [0.0, 17.7, 0.0, 0.0, 0.0]
    bar [0.0, 0.0, 40.8, 0.0, 0.0]
    bar [0.0, 0.0, 0.0, 22.8, 0.0]
    bar [0.0, 0.0, 0.0, 0.0, 9.8]
{% </mermaid> %}
