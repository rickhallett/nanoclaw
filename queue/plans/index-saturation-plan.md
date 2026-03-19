# Plan: Index Saturation (memctl scaling)

Tracking task: 20260317-135614-68c99e93

<plan>
  <goal>Design a solution for INDEX.md scaling beyond ~1000 notes without suffocating the agent on boot</goal>
  
  <steps>
    <step n="1" output="queue/plans/index-saturation-analysis.md">
      Quantify the problem: (1) current INDEX.md size and token count, (2) projection to 1000 notes, (3) boot time impact, (4) which parts of the index are accessed most vs rarely.
    </step>
    <step n="2" output="queue/plans/index-saturation-options.md">
      Enumerate solutions: (1) paginated index with summary page, (2) lazy loading via tag/entity query, (3) tiered hot/warm/cold with recency decay, (4) semantic clustering with representative summaries. Pros/cons for each.
    </step>
    <step n="3" output="queue/plans/index-saturation-recommendation.md">
      Recommend an approach: selected option, migration path from current INDEX.md, backwards compatibility considerations, implementation effort estimate.
    </step>
  </steps>
  
  <constraints>
    <constraint>Design only — do not modify memctl code or INDEX.md</constraint>
    <constraint>Solution must preserve the "lookup protocol" concept from current design</constraint>
    <constraint>Consider that multiple agents may read the index concurrently</constraint>
  </constraints>
  
  <success>
    <criterion>Analysis includes concrete token counts and projections</criterion>
    <criterion>At least 3 distinct options are evaluated</criterion>
    <criterion>Recommendation includes migration path, not just end state</criterion>
  </success>
</plan>
