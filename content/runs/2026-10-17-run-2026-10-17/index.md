---
title: "Toronto - Easy Run"
date: 2026-10-17
draft: false
taxonomies:
  categories: ["runs"]
extra:
  hide_table_of_contents: true
  garmin_activity_id: 24761451705
  distance_km: 5.94
  duration: "31:47"
  pace_per_km: "5:21"
  elevation_gain_m: 22
  mermaid: true
  hr_zones:
    - { zone: 5, name: "Maximum", pct: 2.7 }
    - { zone: 4, name: "Threshold", pct: 0.2 }
    - { zone: 3, name: "Aerobic", pct: 16.7 }
    - { zone: 2, name: "Easy", pct: 63.9 }
    - { zone: 1, name: "Warm Up", pct: 16.5 }
  intervals:
    - { lap: 1, distance_km: "1.00", duration: "5:25", pace: "5:25" }
    - { lap: 2, distance_km: "0.83", duration: "4:35", pace: "5:29" }
    - { lap: 3, distance_km: "1.00", duration: "5:29", pace: "5:29" }
    - { lap: 4, distance_km: "1.00", duration: "5:31", pace: "5:31" }
    - { lap: 5, distance_km: "0.71", duration: "4:00", pace: "5:37" }
    - { lap: 6, distance_km: "0.39", duration: "1:15", pace: "3:14" }
    - { lap: 7, distance_km: "1.00", duration: "5:30", pace: "5:30" }
---
Easy run + one rep of 400m because it's fun and its been a while.

The post-run pizza craving kicked in on the way home.

| Stat | Value |
|------|-------|
| Distance | 5.94 km |
| Duration | 31:47 |
| Pace | 5:21 /km |
| Elevation Gain | 22 m |

## Route

{{ <image path="/runs/maps/24761451705.svg" width={640} /> }}

## Intervals

{% <mermaid labels="mm:ss"> %}
---
config:
  xyChart:
    showDataLabel: true
---
xychart
    title "Pace per Interval (min/km)"
    x-axis ["Lap 1 · 1.00 km", "Lap 2 · 0.83 km", "Lap 3 · 1.00 km", "Lap 4 · 1.00 km", "Lap 5 · 0.71 km", "Lap 6 · 0.39 km", "Lap 7 · 1.00 km"]
    y-axis "min/km" 0 --> 6
    bar [5.423, 5.488, 5.490, 5.511, 5.620, 3.227, 5.492]
{% </mermaid> %}

## Heart Rate Zones

{% <mermaid> %}
xychart horizontal
    title "Time in Heart Rate Zones (%)"
    x-axis ["Zone 5 Maximum", "Zone 4 Threshold", "Zone 3 Aerobic", "Zone 2 Easy", "Zone 1 Warm Up"]
    y-axis "%" 0 --> 100
    bar [2.7, 0.2, 16.7, 63.9, 16.5]
{% </mermaid> %}
