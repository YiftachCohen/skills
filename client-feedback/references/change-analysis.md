# Change/feature analysis playbook

Load this only when classification = `feature` or `change`, and verdict = `valid change`. Otherwise stay in `SKILL.md`.

The point of this file: figure out what changing this *actually* costs across the whole system, and propose the smallest implementation that delivers the spirit of the request.

A "feature request" is rarely just code in one file. The real cost is usually in the seams: schema changes, i18n, permissions, billing, analytics, tests, and existing-user data.

## Step 1 — What does the request actually mean?

Before designing anything, restate the request as a behavior change.

> "The dashboard should also show submitted scholarships, not only new ones"
> → Behavior change: `DashboardScholarships` should include rows where `userScholarship.status IN ('submitted', 'in_review', ...)`, not only `'new'`. Sort and visual treatment likely need to differentiate the two.

Force yourself to write the change as **before/after behavior**, not as "add a feature".

## Step 2 — Impact analysis (the matrix)

Walk every layer. For each, write either the impact or "none" — don't skip.

- **UI / pages affected.** Which routes, which components? Empty states, loading states, error states all need consideration.
- **i18n / strings.** New keys needed? Hebrew + English? RTL implications? (Houston: `lib/i18n/locales/he.ts`.)
- **Server actions / API routes.** Which actions need new params, new return shapes? Backwards compatibility for in-flight callers?
- **Domain services.** Logic that needs to move or change?
- **Database schema.** New columns/tables/indexes? Migration order? Backfill needed for existing rows?
- **Permissions / roles.** Which roles can see/do this? Admin-only? User-tier gated? (Houston: subscription plans, `config/subscriptions.ts`.)
- **Plan-access / billing.** Is this a feature flag for paid tiers? Does it affect upgrade incentives?
- **Auth / session.** New scopes, new session data, token changes?
- **Analytics / tracking.** New events to fire? Existing events whose meaning changes?
- **Email / notifications.** New templates? Variables to pass through? (Houston: Resend + Mustache.)
- **Tests.** Which existing tests break? What new tests are needed? Unit vs integration vs e2e split.
- **Caching / revalidation.** Next.js route segments to mark dynamic, tags to invalidate, etc.
- **SEO / sitemap / structured data.** If any new public pages.
- **Performance.** Query cost, bundle size, payload size.
- **Migration for existing users.** Will existing data appear correctly under the new behavior? Do old records need fields filled in?

This step is the deliverable. It is more valuable than the implementation sketch, because it's how you discover that "small feature" requires touching 8 layers.

## Step 3 — Implementation sketch

Now propose the smallest cohesive implementation. Order matters — list steps in an order that's safe to land:

```
1. Schema migration (new column / table)
2. Backfill (if needed) with verification query
3. Server action / service logic update (gated behind a flag if risky)
4. UI changes
5. i18n strings
6. Tests
7. Analytics events
8. Flag flip / release
```

For each step, name the key files and a rough function/component signature where useful. Don't write the actual implementation — sketch it.

Estimate complexity:
- **S** — < 1 day, 1 file or two.
- **M** — 1–3 days, multiple layers, no migration risk.
- **L** — > 3 days, schema migration, multiple touchpoints, or cross-team coordination.

If you find yourself estimating L for a request the user described as "small", say so explicitly. That's actionable signal.

## Step 4 — Alternatives

Always offer at least two:

1. **Cheaper alternative** — a smaller version that captures most of the spirit. Often this is "show this in an existing surface instead of building a new one" or "wait until a user asks twice before building".
2. **More-ambitious version** — what does the same effort buy if expanded slightly? Often this is "while we're touching this surface, also add Y, which is much cheaper now than later".

Compare on: scope delivered, total effort, risk, optionality preserved.

## Step 5 — Risks and unknowns

- What could go wrong in production? (Migration races, slow query, regressed permissions.)
- What do you not know without asking the user/PM/client? List the questions explicitly.
- Is there a non-code answer? (Documentation, in-app tooltip, a quick admin tool.)

## Output for the SKILL.md `## Analysis` section

```markdown
### Behavior change
Before: <current behavior>
After: <proposed behavior>

### Impact analysis
- UI: <or "none">
- i18n: <or "none">
- Server actions / API: <or "none">
- DB / schema: <or "none">
- Permissions / billing: <or "none">
- Analytics: <or "none">
- Email / notifications: <or "none">
- Tests: <list>
- Migration for existing data: <or "none">
- Performance / caching: <or "none">

### Implementation sketch (complexity: S | M | L)
1. <step> — <files / signatures>
2. ...

### Alternatives
- **Cheaper:** <description, tradeoff>
- **More ambitious:** <description, tradeoff>

### Risks & open questions
- <risk>
- <question for client/PM>
```
