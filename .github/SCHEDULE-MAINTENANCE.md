# Scheduled monitor continuity

GitHub disables public-repository schedules after 60 days without repository
activity. A successful weekly run alone is not sufficient. The independent
`maintain-schedule` job makes an empty commit only after 30 days without commits,
even when the SEC monitor fails. It never changes financial state or sends alerts.
It uses the existing contents permission, no new secret, and no force push.
Branch protection can reject the push; treat a failed maintenance job as actionable.

This job cannot run once GitHub disables the schedule. An external Codex heartbeat
named **Guard AI server monitor schedule** checks weekly on Mondays at 09:00
America/Chicago. It checks workflow status and recent runs, restores only
`disabled_inactivity`, and supplies repository activity if maintenance has stopped.
It respects a deliberate manual disable. This depends on Codex being available and
having GitHub access; it is not an always-on hosted uptime guarantee.

Manual recovery: open Actions > AI Server Commoditization Monitor > Enable workflow,
or use `gh workflow enable monitor.yml --repo manxeon31/ai-server-commoditization`.
Confirm the workflow state is `active` and check the next scheduled run. Do not
dispatch the monitor solely as a keepalive: a completed cycle can send alerts.

The weekly schedule remains Saturday 13:17 UTC. Do not add another scheduled
workflow in this repository as the only recovery mechanism; it shares the same
inactivity failure mode.
