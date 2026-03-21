---
title: "CLI/TUI Email Clients for Arch Linux with Gmail"
category: analysis
status: active
created: 2026-03-21
---

# CLI/TUI Email Clients for Arch Linux with Gmail

**Date:** 2026-03-21
**Context:** Research into terminal email clients suitable for daily Gmail usage on Arch Linux.

---

## Gmail Authentication Landscape (2025-2026)

Before comparing clients, the auth situation matters. As of September 30, 2024, Google killed "less secure apps" (basic password auth) for IMAP/SMTP/POP. Two paths remain:

1. **App Passwords** -- Still work. Require 2FA enabled on your Google account, then generate a per-app password. Simple, widely supported, no expiry headaches.
2. **OAuth2** -- The "proper" way. Requires creating a Google Cloud project, enabling the Gmail API, getting client credentials. More secure, auto-refreshes tokens, but setup is considerably more involved.

**Bottom line:** App passwords are not deprecated and remain the path of least resistance for CLI clients. OAuth2 is better if you want to avoid storing a static credential.

Sources: [Google Workspace transition guide](https://support.google.com/a/answer/14114704), [Gmail OAuth 2.0 changes 2026](https://www.getmailbird.com/gmail-oauth-authentication-changes-user-guide/)

---

## Client Comparison

### 1. NeoMutt

**What it is:** Feature-rich fork of Mutt with 30+ patches integrated (sidebar, notmuch, STRSTRSTRSTRSTRSTR, etc.). The de facto standard for terminal email power users.

**Gmail setup:**
- App passwords via IMAP/SMTP: well-documented, works out of the box
- OAuth2: supported via Google's `oauth2.py` helper script. Requires Python, gpg, and manual token bootstrapping. Functional but not seamless.
- Offline via `isync`/`mbsync` + Maildir is the recommended production setup
- [mutt-wizard](https://github.com/LukeSmithxyz/mutt-wizard) automates the full stack (neomutt + isync + msmtp + pass)

**TUI quality:**
- Threading: excellent, with multiple threading modes
- Search: native search + notmuch integration for full-text indexing
- Keybindings: fully customizable, Vim-style or custom
- Attachments: solid MIME handling, configurable mailcap
- Macros: powerful macro system for automation

**Arch availability:** `neomutt` in official repos. `neomutt-git` in AUR.

**Maintenance:** Very active. Regular releases. Large contributor base.

**Pros:**
- Most mature and battle-tested option
- Enormous ecosystem (guides, configs, scripts)
- mutt-wizard makes initial setup nearly turnkey
- notmuch integration gives you Gmail-level search locally

**Cons:**
- Configuration is muttrc — powerful but verbose and arcane
- OAuth2 setup requires gluing together multiple tools
- Learning curve is steep if you have no mutt background
- The config language has accumulated 25 years of quirks

Sources: [NeoMutt optional features](https://neomutt.org/guide/optionalfeatures.html), [NeoMutt + notmuch + mbsync guide](https://cosroe.com/2025/04/neomutt-notmuch-mbsync.html), [SeniorMars neomutt guide](https://seniormars.com/posts/neomutt/)

---

### 2. aerc

**What it is:** Modern terminal email client written in Go. Vim-style keybindings, embedded terminal for composing, tab-based UI. Created by Drew DeVault (sway, sr.ht).

**Gmail setup:**
- App passwords: straightforward, well-documented on the [aerc wiki](https://man.sr.ht/~rjarry/aerc/providers/gmail.md)
- OAuth2: supported natively. Documented setup via Google Cloud console.
- Built-in account wizard (`aerc new-account`) walks you through setup
- Direct IMAP — no external sync tool required (though Maildir/notmuch backends exist)

**TUI quality:**
- Threading: built-in, toggleable, works with or without server-side threading
- Search: IMAP server-side search. Local search via notmuch if using Maildir backend.
- Keybindings: Vim-style with ex-command bar. Fully configurable via `binds.conf`.
- Attachments: handled well. Embedded terminal means you can pipe to anything.
- Tabs: multiple accounts/views simultaneously
- Filters: built-in message filters (HTML rendering, syntax highlighting for patches)

**Arch availability:** `aerc` in official repos.

**Maintenance:** Very active. FOSDEM 2025 talk. Regular releases. Healthy contributor base.

**Pros:**
- Cleanest onboarding experience of any terminal email client
- Direct IMAP means fewer moving parts than the neomutt+isync stack
- Embedded terminal composition is genuinely pleasant
- Sane defaults — usable immediately, customizable later
- Tab-based UI is natural for multi-account use
- Patch workflow support (git send-email integration)

**Cons:**
- Younger than (neo)mutt — fewer community configs and guides
- IMAP search is limited compared to notmuch full-text indexing
- No offline mode without switching to Maildir backend + isync
- Plugin ecosystem is smaller

Sources: [aerc official site](https://aerc-mail.org/), [aerc ArchWiki](https://wiki.archlinux.org/title/Aerc), [FOSDEM 2025 talk](https://aerc-mail.org/fosdem-2025/), [aerc Gmail guide](https://man.sr.ht/~rjarry/aerc/providers/gmail.md)

---

### 3. Himalaya

**What it is:** CLI email tool written in Rust. Not a TUI — it is a stateless command-line interface. You run commands like `himalaya list`, `himalaya read 42`, `himalaya send`. Designed for scripting and composition with other tools.

**Gmail setup:**
- OAuth2: first-class support via built-in OAuth2 proxy
- App passwords: supported via standard IMAP/SMTP config
- JMAP backend support (forward-looking)
- Configuration via TOML file

**TUI quality:**
- No TUI. This is a CLI tool. You interact via shell commands.
- Pairs with `himalaya-repl` for a more interactive experience
- JSON output mode for scripting and piping
- Composition via `$EDITOR`

**Arch availability:** `himalaya` in AUR. Also available via cargo install.

**Maintenance:** Active. v0.5.x released in 2025. Part of the broader Pimalaya project.

**Pros:**
- Best-in-class for scripting and automation
- JSON output makes it composable with jq, fzf, etc.
- Rust binary — fast, no runtime dependencies
- OAuth2 is a first-class citizen, not bolted on
- JMAP support is forward-looking

**Cons:**
- Not a mail reader in the traditional sense — no persistent UI
- Reading long threads is awkward via CLI invocations
- Smaller community than mutt/aerc
- AUR only (not in official Arch repos)

Sources: [Himalaya GitHub](https://github.com/pimalaya/himalaya), [Himalaya OAuth2 guide](https://lobstermail.ai/blog/himalaya-oauth2-how-to-set-up-gmail-and-outlook-email-auth-from-the-cli)

---

### 4. Mutt (classic)

**What it is:** The original. Text-based email client since 1995. Still maintained, still works.

**Gmail setup:** Same as NeoMutt (app passwords or OAuth2 via helper scripts).

**Arch availability:** `mutt` in official repos.

**Maintenance:** Maintained but slow-moving. NeoMutt has absorbed most community energy.

**Verdict:** No reason to choose Mutt over NeoMutt in 2026 unless you specifically need the vanilla codebase. NeoMutt is a strict superset with better defaults. Covering Mutt separately is academic at this point.

Sources: [Mutt ArchWiki](https://wiki.archlinux.org/title/Mutt)

---

### 5. meli

**What it is:** Terminal email client written in Rust. Aims to be a modern mutt-like client with sane defaults. Supports IMAP, JMAP, Maildir, mbox, notmuch.

**Gmail setup:**
- IMAP/SMTP with app passwords
- JMAP backend available
- OAuth2 status unclear — documentation does not prominently feature it
- Configuration via TOML

**TUI quality:**
- Threading: supported
- Search: notmuch integration available
- Keybindings: customizable
- Attachments: MIME support
- Notifications via dbus
- PGP via libgpgme

**Arch availability:** `meli` in AUR. `meli-git` also in AUR.

**Maintenance:** Active. v0.8.13 released January 2026. Sole maintainer (Mstrstrstrstrstrstrstrstr Strstrstrstrstr) — bus factor of 1.

**Pros:**
- Modern Rust codebase, actively developed
- JMAP support (future-proofing)
- Sane defaults, less configuration ceremony than neomutt
- notmuch integration built in

**Cons:**
- Pre-1.0 — API and config format may change
- Small community, limited documentation
- OAuth2 support is not well-documented for Gmail specifically
- AUR only
- Single maintainer — sustainability risk

Sources: [meli official site](https://meli-email.org/), [meli GitHub](https://github.com/meli/meli)

---

### 6. notmuch (with frontends: alot, neomutt, emacs)

**What it is:** Not a mail client. It is a mail indexer and search engine built on Xapian. You pair it with a sync tool (isync/mbsync, offlineimap) and a frontend.

**Gmail setup:** notmuch itself does not fetch mail. You need:
1. `isync`/`mbsync` to sync Gmail via IMAP to local Maildir
2. `notmuch new` to index
3. A frontend to read/compose

**Frontends:**

| Frontend | Language | Status | Notes |
|----------|----------|--------|-------|
| **neomutt** | C | Active, excellent | Best option. Uses notmuch as virtual mailboxes. |
| **alot** | Python | Maintained but slow | Curses-based. Ships with a Sup theme. Functional but sluggish on large mailboxes. |
| **emacs (notmuch.el)** | Elisp | Very active | Best notmuch frontend if you live in Emacs. |
| **astroid** | C++ | Stale | Last meaningful release was 2021. Not recommended. |

**Arch availability:** `notmuch` in official repos. `alot` in official repos. Frontend-specific packages available.

**Maintenance:** notmuch core is actively maintained. Frontend health varies (see table above).

**Pros:**
- Best search of any option (Xapian full-text indexing)
- Tag-based workflow (labels, not folders) maps naturally to Gmail's model
- Decoupled architecture — swap any component
- Offline-first by design

**Cons:**
- Not a single tool — you are assembling a pipeline (sync + index + frontend + send)
- Setup complexity is highest of all options
- alot as a standalone frontend is underwhelming compared to aerc or neomutt
- Multiple moving parts means multiple failure modes

Sources: [notmuch ArchWiki](https://wiki.archlinux.org/title/Notmuch), [notmuch frontends](https://notmuchmail.org/frontends/), [NeoMutt notmuch feature](https://neomutt.org/feature/notmuch)

---

### 7. sup

**What it is:** Curses-based, threads-with-tags email client written in Ruby. Pioneered the tag-based workflow that notmuch later adopted.

**Gmail setup:** IMAP via Ruby libraries. No OAuth2 support.

**Arch availability:** AUR (`sup-mail`).

**Maintenance:** Effectively dead. The GitHub repo (`sup-heliotrope/sup`) has minimal recent activity. The notmuch ecosystem is the spiritual successor.

**Verdict:** Historical interest only. Do not use for new setups in 2026. If you liked sup's model, use notmuch + neomutt or notmuch + alot instead.

Sources: [sup GitHub](https://github.com/sup-heliotrope/sup)

---

### 8. Alpine

**What it is:** Successor to Pine. Developed at University of Washington. Menu-driven TUI with built-in IMAP/SMTP.

**Gmail setup:**
- IMAP/SMTP with app passwords: works, well-documented
- OAuth2: not supported
- Built-in configuration menu (no config files to hand-edit)

**TUI quality:**
- Menu-driven, not Vim-style — closer to a traditional application
- Threading: basic
- Search: IMAP server-side only
- Attachments: functional
- Keybindings: fixed menu-based, not customizable in the Vim sense

**Arch availability:** `alpine` in AUR. `re-alpine` also in AUR.

**Maintenance:** University of Washington stopped active development in 2008. Community patches exist but development is glacial.

**Verdict:** Works if you already know Pine/Alpine and want something familiar. Not recommended for new users in 2026. The lack of OAuth2 means you are locked into app passwords, and the lack of active development means security issues may go unpatched.

Sources: [Alpine Wikipedia](https://en.wikipedia.org/wiki/Alpine_(email_client))

---

## Honorable Mentions

| Client | What it is | Why you might care | Why you probably won't |
|--------|-----------|-------------------|----------------------|
| **mu/mu4e** | Emacs-based email client using mu (Xapian indexer) | Excellent if you already live in Emacs. Great search. | Requires Emacs. Not a standalone terminal client. |
| **himalaya-repl** | REPL wrapper around himalaya | More interactive than raw himalaya CLI | Very early stage |
| **mutt-wizard** | Not a client — an installer | Automates neomutt+isync+msmtp+pass stack | Opinionated setup, may conflict with existing configs |
| **mbstrstrstrstrstrstrstrstrstrstrstrstrstrstr** (catstrstrstrstrstrstrstrstr) | JMAP-first email management tool | JMAP is Gmail's future direction | Extremely niche, limited documentation |

---

## Comparison Matrix

| Criterion | NeoMutt | aerc | himalaya | meli | notmuch stack | Alpine |
|-----------|---------|------|----------|------|---------------|--------|
| **Gmail OAuth2** | Via script | Native | Native | Unclear | Via sync tool | No |
| **App passwords** | Yes | Yes | Yes | Yes | Yes | Yes |
| **Offline mode** | Via isync | Via Maildir backend | No | Via Maildir | Yes (core design) | No |
| **Threading** | Excellent | Good | N/A (CLI) | Good | Excellent | Basic |
| **Search** | Good + notmuch | IMAP only | IMAP only | Good + notmuch | Best (Xapian) | IMAP only |
| **Arch repo** | Official | Official | AUR | AUR | Official | AUR |
| **Config complexity** | High | Low-Medium | Low | Medium | Very High | Low |
| **Learning curve** | Steep | Moderate | Low | Moderate | Steep | Gentle |
| **Maintenance** | Very active | Very active | Active | Active (1 dev) | Active | Dormant |
| **Scripting/automation** | Macros | Filters/pipes | Best (JSON) | Limited | Tag scripts | No |

---

## Recommendation

**For daily Gmail usage on Arch Linux in 2026, two options stand out:**

### Primary: aerc

If you want a single, self-contained terminal email client with minimal setup friction, aerc is the best current option. Native OAuth2, built-in account wizard, direct IMAP (no sync daemon needed), Vim keybindings, and it is in the official Arch repos. The tradeoff is weaker search (no local full-text indexing unless you add notmuch) and no offline mode without extra tooling.

### Power user: NeoMutt + isync + notmuch

If you want Gmail-grade search locally, offline access, and maximum configurability, the neomutt stack is unmatched. The cost is setup complexity — you are assembling and maintaining a pipeline of 3-4 tools. mutt-wizard can bootstrap this, but you will inevitably need to understand the pieces when something breaks.

### Scripting/automation: himalaya

If the primary use case is programmatic email access (reading mail from scripts, piping to other tools, JSON output), himalaya is purpose-built for this and nothing else comes close.

### Skip: Alpine, sup, classic Mutt

Alpine and sup are historical artifacts. Classic Mutt is superseded by NeoMutt.

### Watch: meli

Promising Rust client with JMAP support, but pre-1.0 with a single maintainer. Worth revisiting in a year.

---

## Open Questions

1. **Google app password longevity** -- App passwords still work as of March 2026, but Google has been on a slow march toward OAuth2-only. If app passwords are eventually killed, clients without native OAuth2 (Alpine, sup) become non-viable, and clients with bolted-on OAuth2 (neomutt) become more painful.

2. **JMAP adoption** -- Gmail does not currently expose a public JMAP endpoint. If/when it does, clients with JMAP support (meli, himalaya) gain a significant advantage over IMAP-only clients. This would be the single biggest disruption to the landscape.

3. **aerc offline story** -- aerc's direct-IMAP approach is clean but means no offline access. For laptop/travel use, this matters. The Maildir backend exists but is less documented.
