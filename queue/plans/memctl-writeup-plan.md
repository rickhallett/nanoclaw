# Plan: Memctl Write-up for External Audience

Tracking task: 20260316-082712

<plan>
  <goal>Transform the internal memctl architecture doc into a polished external write-up suitable for blog/portfolio</goal>
  
  <steps>
    <step n="1" output="queue/plans/memctl-writeup-outline.md">
      Read docs/d1/memctl-architecture-overview.md and extract: (1) the novel contributions (enrichment rubric, enforcement loop, rebuild invariant), (2) the problem statement for external readers, (3) candidate hooks/angles for the piece.
    </step>
    <step n="2" output="queue/plans/memctl-writeup-draft.md">
      Write first draft: ~1500 words, conversational but technical, structured as problem → insight → mechanism → results. Include one concrete example of the enrichment rubric in action.
    </step>
    <step n="3" output="queue/plans/memctl-writeup-review-notes.md">
      Self-review the draft: flag jargon that needs definition, identify missing context for external readers, note where diagrams would help.
    </step>
  </steps>
  
  <constraints>
    <constraint>Writing task only — do not modify memctl code or existing docs</constraint>
    <constraint>Target audience: technical readers unfamiliar with NanoClaw internals</constraint>
    <constraint>Outputs go to queue/plans/, not docs/ (human will place final version)</constraint>
  </constraints>
  
  <success>
    <criterion>Draft document exists and is coherent standalone</criterion>
    <criterion>The "what is novel" section is clearly articulated</criterion>
    <criterion>Review notes identify at least 3 specific improvements</criterion>
  </success>
</plan>
