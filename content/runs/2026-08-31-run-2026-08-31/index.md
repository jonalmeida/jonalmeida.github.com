---
title: "Seville Running"
date: 2026-08-31
draft: false
taxonomies:
  categories: ["runs"]
extra:
  hide_table_of_contents: true
  garmin_activity_id: 24179982071
  distance_km: 4.54
  duration: "33:49"
  pace_per_km: "7:27"
  elevation_gain_m: 11
  mermaid: true
  hr_zones:
    - { zone: 5, name: "Maximum", pct: 0.0 }
    - { zone: 4, name: "Threshold", pct: 0.0 }
    - { zone: 3, name: "Aerobic", pct: 0.0 }
    - { zone: 2, name: "Easy", pct: 0.0 }
    - { zone: 1, name: "Warm Up", pct: 0.0 }
---
Nice day, flat route, matcha recovery. 

{{ <gallery page={page} /> }}

| Stat | Value |
|------|-------|
| Distance | 4.54 km |
| Duration | 33:49 |
| Pace | 7:27 /km |
| Elevation Gain | 11 m |

## Route

{{ <image path="/runs/maps/24179982071.svg" width={640} /> }}

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
    bar [0.0, 0.0, 0.0, 0.0, 0.0]
    bar [0.0, 0.0, 0.0, 0.0, 0.0]
{% </mermaid> %}
