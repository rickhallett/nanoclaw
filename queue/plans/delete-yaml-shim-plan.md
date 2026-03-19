# Plan: Delete yaml_shim.py

Tracking task: 20260317-134708-a3cffe91

<plan>
  <goal>Delete halos/nightctl/yaml_shim.py and update all imports to use PyYAML directly</goal>
  
  <steps>
    <step n="1" output="queue/plans/delete-yaml-shim-imports.txt">
      Search for all files importing yaml_shim. List each file path and the exact import pattern used.
    </step>
    <step n="2" output="queue/plans/delete-yaml-shim-edits.diff">
      For each file: remove the try/except ImportError block and replace with a direct `import yaml` statement. Preserve the yaml.safe_load and yaml.dump usage patterns (they're compatible).
    </step>
    <step n="3" output="queue/plans/delete-yaml-shim-deletion.txt">
      Delete halos/nightctl/yaml_shim.py
    </step>
    <step n="4" output="queue/plans/delete-yaml-shim-verify.txt">
      Run: uv run python -c "from halos.nightctl import cli, item, job, manifest, archive, config, container, executor, migrate_todoctl; from halos.halctl import config as hc, renderer, provision, eval_harness; print('All imports OK')"
    </step>
    <step n="5" output="queue/plans/delete-yaml-shim-gate.txt">
      Run: make gate (or equivalent: uv run pytest halos/ -q)
    </step>
  </steps>
  
  <constraints>
    <constraint>Do not modify any yaml.safe_load or yaml.dump call sites — only the import statements</constraint>
    <constraint>Do not add new dependencies — PyYAML is already in pyproject.toml</constraint>
    <constraint>All 13 import sites must be updated atomically (no partial state)</constraint>
  </constraints>
  
  <success>
    <criterion>yaml_shim.py no longer exists</criterion>
    <criterion>All halos modules import successfully</criterion>
    <criterion>Tests pass (make gate or pytest)</criterion>
  </success>
</plan>
