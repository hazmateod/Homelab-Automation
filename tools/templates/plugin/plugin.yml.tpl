---
name: {{ name }}

display_name: {{ display_name }}

version: 1.0.0

author: Homelab Infrastructure Management Platform

description: >
  {{ display_name }} plugin.

entrypoint: tasks/main.yml

inventory_group: {{ inventory_group }}

supports:
  discovery: true
  health: true
  reporting: true

artifacts: []

requirements: []
