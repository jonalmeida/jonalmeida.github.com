---
title: "Mississauga Running"
date: 2026-09-12
draft: false
taxonomies:
  categories: ["runs"]
extra:
  hide_table_of_contents: true
  garmin_activity_id: 24339397572
  distance_km: 5.02
  duration: "26:50"
  pace_per_km: "5:21"
  elevation_gain_m: 37
  mermaid: true
  hr_zones:
    - { zone: 5, name: "Maximum", pct: 0.0 }
    - { zone: 4, name: "Threshold", pct: 0.0 }
    - { zone: 3, name: "Aerobic", pct: 0.0 }
    - { zone: 2, name: "Easy", pct: 7.0 }
    - { zone: 1, name: "Warm Up", pct: 93.0 }
---
Post-pizza nap. Should have gone earlier in the morning when it was less muggy, and I was fresher.

Good run despite that.

Neighborhood has now grown backyard bouncy castles. 🏰

{{ <gallery page={page} /> }}

| Stat | Value |
|------|-------|
| Distance | 5.02 km |
| Duration | 26:50 |
| Pace | 5:21 /km |
| Elevation Gain | 37 m |

## Route

{{ <image path="/runs/maps/24339397572.svg" width={640} /> }}

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
    bar [0.0, 0.0, 0.0, 0.0, 0.0]
    bar [0.0, 0.0, 0.0, 7.0, 0.0]
    bar [0.0, 0.0, 0.0, 0.0, 93.0]
{% </mermaid> %}
