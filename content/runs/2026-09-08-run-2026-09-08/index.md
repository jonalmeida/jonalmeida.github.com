---
title: "Patagonia run club"
date: 2026-09-08
draft: false
taxonomies:
  categories: ["runs"]
extra:
  hide_table_of_contents: true
  garmin_activity_id: 24290984956
  distance_km: 5.2
  duration: "30:02"
  pace_per_km: "5:46"
  elevation_gain_m: 23
  mermaid: true
  hr_zones:
    - { zone: 5, name: "Maximum", pct: 0.0 }
    - { zone: 4, name: "Threshold", pct: 0.0 }
    - { zone: 3, name: "Aerobic", pct: 0.0 }
    - { zone: 2, name: "Easy", pct: 0.0 }
    - { zone: 1, name: "Warm Up", pct: 100.0 }
---
Yup, HRM strap to prove the wrist monitor is no bueno.

A weird pain at the top of left foot from the Saucony Pros that I've never felt before. Maybe it's because I usually wear them for the speed work? First pair of shoes I've worn that are not the EVO SL in two weeks, so that could be it.

UPDATE: On a self-diagnosis site with many different foot problems one can have, they have deduced that I have tied-shoelaces-too-tightis. Getting called out by WebMD sites is not flattering. 🥲

{{ <gallery page={page} /> }}

| Stat | Value |
|------|-------|
| Distance | 5.2 km |
| Duration | 30:02 |
| Pace | 5:46 /km |
| Elevation Gain | 23 m |

## Route

{{ <image path="/runs/maps/24290984956.svg" width={640} /> }}

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
    bar [0.0, 0.0, 0.0, 0.0, 100.0]
{% </mermaid> %}
