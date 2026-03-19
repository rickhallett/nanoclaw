# Plan: Dashboard Metrics Wishlist (BATHW)

Tracking task: 20260317-102759-886

<plan>
  <goal>Enumerate capturable metrics for the BATHW dashboard with capture methods, storage formats, and ROI justification</goal>
  
  <steps>
    <step n="1" output="queue/plans/bathw-metrics-inventory.md">
      Survey existing data sources: (1) git log for commit velocity, (2) store/messages.db for conversation pairs, (3) logctl for token usage, (4) nightctl for task completion. List what's already capturable today.
    </step>
    <step n="2" output="queue/plans/bathw-metrics-spec.md">
      For each metric in the wishlist (commits/time, response pairs, token burn with context, scope accuracy), specify: capture method, storage format (time series? aggregates?), query patterns, and what hypotheses it tests.
    </step>
    <step n="3" output="queue/plans/bathw-metrics-gaps.md">
      Identify gaps: what signals would be valuable but aren't currently captured? Propose lightweight instrumentation points. Estimate effort for each.
    </step>
  </steps>
  
  <constraints>
    <constraint>Research and specification only — do not implement capture code</constraint>
    <constraint>Output is a reference doc for future implementation, not a working system</constraint>
    <constraint>Focus on signals that inform human decision-making, not vanity metrics</constraint>
  </constraints>
  
  <success>
    <criterion>Metrics spec covers all four items from original context</criterion>
    <criterion>Each metric has a concrete capture method, not just "track X"</criterion>
    <criterion>Gaps document proposes at least 2 additional high-value signals</criterion>
  </success>
</plan>
