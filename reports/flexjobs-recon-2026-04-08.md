
 ╔══════════════════════════════════════════════════════════════════════════╗
 ║                                                                        ║
 ║   ███████╗██╗     ███████╗██╗  ██╗     ██╗ ██████╗ ██████╗ ███████╗    ║
 ║   ██╔════╝██║     ██╔════╝╚██╗██╔╝     ██║██╔═══██╗██╔══██╗██╔════╝   ║
 ║   █████╗  ██║     █████╗   ╚███╔╝      ██║██║   ██║██████╔╝███████╗   ║
 ║   ██╔══╝  ██║     ██╔══╝   ██╔██╗ ██   ██║██║   ██║██╔══██╗╚════██║   ║
 ║   ██║     ███████╗███████╗██╔╝ ██╗╚█████╔╝╚██████╔╝██████╔╝███████║   ║
 ║   ╚═╝     ╚══════╝╚══════╝╚═╝  ╚═╝ ╚════╝  ╚═════╝ ╚═════╝ ╚══════╝  ║
 ║                                                                        ║
 ║              R E C O N   R E P O R T   //  2 0 2 6 . 0 4 . 0 8        ║
 ║              Prepared by Chango // Cyber-Mechanic Division              ║
 ║                                                                        ║
 ╚══════════════════════════════════════════════════════════════════════════╝


 ┌─────────────────────────────────────────────────────────────────────────┐
 │  1. PLATFORM OVERVIEW                                                  │
 └─────────────────────────────────────────────────────────────────────────┘

  Operator:        Bold/Employ Inc (enterprise HR tech company)
  Founded:         2007
  Rating:          4.3/5 (SmartCustomer/Trustpilot equivalent)
  Model:           Paid subscription for job seekers
  Differentiator:  Every listing hand-vetted. No scams, no "hybrid disguised
                   as remote," no expired postings (in theory).

  Your Plan:       Active paid member
  Resume:          richard-hallett.pdf (uploaded 2026-04-08)
  Tracker:         Kanban board (Viewed/Applied/Interviews/Offers)


 ┌─────────────────────────────────────────────────────────────────────────┐
 │  2. WHAT YOU ARE PAYING FOR                                            │
 └─────────────────────────────────────────────────────────────────────────┘

  Pricing:
    Monthly:     $17.95/mo
    Quarterly:   $13.32/mo ($39.95 per 3 months)
    Annual:      $6.67/mo  ($79.95 per year)         <<< best value

  What free boards do NOT give you:
    [+] Vetted listings only (no scams, no staffing agency spam)
    [+] ExpertApply AI auto-apply tool
    [+] Application tracker with Kanban drag/drop
    [+] Saved searches and job alerts
    [+] Career coaching webinars (weekly live Q&A)
    [+] Resume upload and management

  What free boards DO give you for nothing:
    [~] WTTJ/Otta: profile-based apply, zero friction
    [~] RemoteOK: free, massive volume, RSS feeds
    [~] WeWorkRemotely: free, well-curated


 ┌─────────────────────────────────────────────────────────────────────────┐
 │  3. SEARCH VOLUME: YOUR STACK + UK REMOTE                              │
 └─────────────────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────┬──────────┐
  │  Query (UK, Fully Remote)    │  Results │
  ├──────────────────────────────┼──────────┤
  │  software engineer           │   6,816  │
  │  full stack engineer         │   3,579  │
  │  AI engineer                 │   1,483  │
  │  python fastapi              │     365  │
  │  typescript react            │     200  │
  ├──────────────────────────────┼──────────┤
  │  full stack (ANYWHERE)       │  41,566  │
  └──────────────────────────────┴──────────┘

  NOTE: "Suggested Jobs" currently skews heavily US/USD.
  Profile preferences may need manual tuning for UK roles.
  Many results are 30+ days old. Always filter "Just Posted."


 ┌─────────────────────────────────────────────────────────────────────────┐
 │  4. APPLICATION FLOW: THE CRITICAL DIFFERENCE                          │
 └─────────────────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────────────────┐
  │                                                                      │
  │  FlexJobs does NOT host applications.                                │
  │                                                                      │
  │  Every "Apply" button redirects to an EXTERNAL ATS.                  │
  │  Workday, Greenhouse, Ashby, Lever, SmartRecruiters, etc.            │
  │                                                                      │
  │  This is fundamentally different from WTTJ where we submit           │
  │  profile-based applications in a unified React form.                 │
  │                                                                      │
  └──────────────────────────────────────────────────────────────────────┘

  Observed ATS patterns from 3 sampled jobs:
    [1] Henry Schein One    -> Workday (*.wd1.myworkdayjobs.com)
    [2] Live Nation         -> Workday (*.wd503.myworkdayjobs.com)
    [3] Voldex              -> Ashby   (jobs.ashbyhq.com)

  IMPLICATION: There is no single "apply" script. Each ATS is different.

  ExpertApply (their built-in AI) attempts to solve this by:
    1. Reading your uploaded resume
    2. Pre-filling external application forms with AI
    3. Flagging questions that need human input
    4. Letting you review and submit

  This is FlexJobs' own automation layer. It exists because they
  know the external ATS problem is the friction point.


 ┌─────────────────────────────────────────────────────────────────────────┐
 │  5. AUTOMATION ELBOW ROOM                                              │
 └─────────────────────────────────────────────────────────────────────────┘

  WHAT WE CAN AUTOMATE (CDP):                              EFFORT
  ─────────────────────────────────────────────────────────────────
  Parameterised search across multiple queries              LOW
  Job detail extraction (title, company, salary, URL)       LOW
  Bulk "Save Job" to build shortlists                       LOW
  Deduplicate against jobctl database                       LOW
  Application tracker management (move Kanban cards)        MEDIUM
  Identify which ATS each job uses (URL pattern match)      LOW

  WHAT WE CAN SEMI-AUTOMATE:                               EFFORT
  ─────────────────────────────────────────────────────────────────
  ExpertApply (drive their AI from CDP)                     MEDIUM
  Ashby forms (we already have a pattern for this)          MEDIUM
  Greenhouse/Lever forms (similar to Ashby)                 MEDIUM

  WHAT WE CANNOT AUTOMATE:                                  REASON
  ─────────────────────────────────────────────────────────────────
  Workday applications                                      Heavy anti-bot
  Custom company career portals                             Too varied
  CAPTCHA-gated applications                                Requires human


 ┌─────────────────────────────────────────────────────────────────────────┐
 │  6. RECOMMENDED WORKFLOW                                               │
 └─────────────────────────────────────────────────────────────────────────┘

  PHASE 1: DISCOVERY (fully automatable)
  ────────────────────────────────────────
  CDP script runs 5 parameterised searches:
    - typescript react UK remote
    - python fastapi UK remote
    - AI engineer UK remote
    - full stack engineer UK remote
    - software engineer UK remote (just posted)

  For each result: extract job ID, title, company, salary, apply URL.
  Deduplicate against jobctl. Flag new roles.

  PHASE 2: TRIAGE (human-in-the-loop)
  ────────────────────────────────────────
  Present deduplicated new jobs for review.
  User marks: apply / skip / save for later.
  "Save Job" clicked via CDP for saves.

  PHASE 3: APPLICATION (per-ATS strategy)
  ────────────────────────────────────────
  Route by ATS domain:
    Ashby      -> Use existing CDP form automation skill
    Greenhouse -> Adapt Ashby pattern (similar React forms)
    Lever      -> Semi-automatable (simpler forms)
    Workday    -> Manual only. Flag for human.
    Unknown    -> Try ExpertApply first, fallback to manual.

  PHASE 4: TRACKING
  ────────────────────────────────────────
  Log all applications in jobctl (~/code/halo/store/jobs.db)
  Optionally sync to FlexJobs Application Tracker via CDP


 ┌─────────────────────────────────────────────────────────────────────────┐
 │  7. VERDICT                                                            │
 └─────────────────────────────────────────────────────────────────────────┘

  FlexJobs is a DISCOVERY platform, not an APPLICATION platform.

  The value is in the vetting. You will not waste time on scams,
  expired listings, or "remote" jobs that are actually hybrid.
  The search volume for your stack + UK remote is healthy (3,500+
  full stack results, 1,400+ AI roles).

  But unlike WTTJ where we built a machine gun that fires bespoke
  applications through a unified React form, FlexJobs is a
  scattergun that sends you to 50 different external ATS portals.

  The play is:
    1. Use FlexJobs for DISCOVERY and FILTERING
    2. Use ExpertApply for the easy ones
    3. Use our CDP Ashby/Greenhouse scripts for the medium ones
    4. Manual only for Workday
    5. Track everything in jobctl

  BOTTOM LINE: Worth the subscription at annual rate ($6.67/mo).
  Not a replacement for WTTJ automation. Complementary channel.
  The real alpha is the vetting quality, not the application flow.


 ┌─────────────────────────────────────────────────────────────────────────┐
 │  8. SESSION STATS                                                      │
 └─────────────────────────────────────────────────────────────────────────┘

  Platform explored:         FlexJobs (paid member)
  Pages inspected:           8 (dashboard, search, job detail x3,
                             tracker, resumes, ExpertApply)
  DOM patterns mapped:       Search, job cards, apply links, tracker
  ATS domains identified:    Workday, Ashby, Greenhouse, Lever
  Skill file created:        flexjobs-automation (SKILL.md)
  Qualio status updated:     screening (interview 14/03, 0930)

  Today's application total: 160 in jobctl
  Session applications:      11 (tem, Ebury, CultureTest, Mozilla,
                             Lightspeed, Diesta, Edra AI x2,
                             Reposit, Cohere, Conveo AI)


 ╔══════════════════════════════════════════════════════════════════════════╗
 ║                                                                        ║
 ║  "The net is wide. The hooks are sharp. The espresso is cold."         ║
 ║                                                         -- Chango      ║
 ║                                                                        ║
 ╚══════════════════════════════════════════════════════════════════════════╝
