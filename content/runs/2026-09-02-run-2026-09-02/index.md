---
title: "Lisbon Running"
date: 2026-09-02
draft: false
taxonomies:
  categories: ["runs"]
extra:
  hide_table_of_contents: true
  garmin_activity_id: 24206823662
  distance_km: 6.03
  duration: "32:29"
  pace_per_km: "5:23"
  elevation_gain_m: 7
  mermaid: true
  hr_zones:
    - { zone: 5, name: "Maximum", pct: 0.0 }
    - { zone: 4, name: "Threshold", pct: 0.0 }
    - { zone: 3, name: "Aerobic", pct: 0.7 }
    - { zone: 2, name: "Easy", pct: 1.8 }
    - { zone: 1, name: "Warm Up", pct: 97.5 }
---
Burning off yesterday's wining and dining. 🐟🍷🍖

{{ <gallery page={page} /> }}

| Stat | Value |
|------|-------|
| Distance | 6.03 km |
| Duration | 32:29 |
| Pace | 5:23 /km |
| Elevation Gain | 7 m |

## Route

{{ <image path="/runs/maps/24206823662.svg" width={640} /> }}

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
    bar [0.0, 0.0, 0.0, 0.0, 0.0]
    bar [0.0, 0.0, 0.0, 0.0, 0.0]
    bar [0.0, 0.0, 0.7, 0.0, 0.0]
    bar [0.0, 0.0, 0.0, 1.8, 0.0]
    bar [0.0, 0.0, 0.0, 0.0, 97.5]
{% </mermaid> %}
