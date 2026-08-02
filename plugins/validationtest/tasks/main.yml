---
###############################################################################
# Plugin Lifecycle
###############################################################################

- name: Execute discovery
  ansible.builtin.include_tasks:
    file: discovery.yml

- name: Execute health
  ansible.builtin.include_tasks:
    file: health.yml

- name: Execute report
  ansible.builtin.include_tasks:
    file: report.yml
