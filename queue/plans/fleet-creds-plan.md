# Plan: Fleet Credential Provisioning Research

Tracking task: 20260317-173416-363dfcc4

<plan>
  <goal>Research non-interactive credential provisioning for gh, vercel, and neonctl to enable automated fleet instance setup</goal>
  
  <steps>
    <step n="1" output="queue/plans/fleet-creds-gh-research.md">
      Research GitHub CLI token provisioning: (1) can gh auth login accept a PAT non-interactively? (2) what scopes are needed for typical dev workflows? (3) how does gh handle token refresh/expiry? Document with examples.
    </step>
    <step n="2" output="queue/plans/fleet-creds-vercel-research.md">
      Research Vercel CLI token provisioning: (1) vercel login --token flow, (2) project-scoped vs account-scoped tokens, (3) team isolation boundaries. Document with examples.
    </step>
    <step n="3" output="queue/plans/fleet-creds-neon-research.md">
      Research Neon alternatives: (1) neonctl auth flow, (2) SQLite as local-first default (already in use), (3) Turso/libSQL as middle ground, (4) when does fleet actually need Neon? Document trade-offs.
    </step>
    <step n="4" output="queue/plans/fleet-creds-rotation.md">
      Research credential lifecycle: (1) rotation strategies per service, (2) revocation on instance teardown, (3) audit trail requirements. Document operational model.
    </step>
    <step n="5" output="queue/plans/fleet-creds-summary.md">
      Synthesize findings into halctl create requirements: what the provisioning script needs to automate, what remains manual, recommended sequence.
    </step>
  </steps>
  
  <constraints>
    <constraint>Research only — do not implement or modify any code</constraint>
    <constraint>Do not create or use real credentials; document the mechanisms</constraint>
    <constraint>Each output file should be self-contained and readable independently</constraint>
  </constraints>
  
  <success>
    <criterion>All five research documents exist with substantive findings</criterion>
    <criterion>Summary document answers the five questions in the original context</criterion>
    <criterion>No code changes, no commits</criterion>
  </success>
</plan>
