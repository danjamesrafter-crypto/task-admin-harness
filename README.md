# Task Admin Console — live harness

Sister app to the [Reader Shell harness](https://github.com/danjamesrafter-crypto/reader-shell-harness). One `index.html`, no build step, no data in the repo.

It runs as a **Flywheel extension app** (Viewer type, matched to projects) and reads data through the Extension SDK's `apiRequest` proxy, so the page never sees a token. It turns the Task Admin Console design prototype into a working page on live data, and records what the 23.x API accepts so the engineering spike starts from evidence.

**Spike harness, not the product.** The product would mount on the site origin (like `/upload/` and the proposed `/reader/`) or become a route in the core app.

## Try it without Flywheel
Open the page with `#demo` on the end of the URL, or click **Use demo data** on the "Not connected" screen. The mock data is shaped like the 23.x responses, and nothing is sent anywhere.

## Host it (GitHub Pages)
1. Create a public repo, e.g. `task-admin-harness`, and upload `index.html` and this README.
2. Go to **Settings → Pages**, deploy from the `main` branch, root folder.
3. The page goes live at `https://<user>.github.io/task-admin-harness/`.

## Register it on a site (admin)
**Admin → Applications → Register New Application**
- Type: **Viewer** · Name: **Task Admin Console (harness)** · URL: the Pages link · Match: **Project** containers
- Application options (optional JSON):

```json
{
  "typical_minutes": [12, 30],
  "pace_floor_minutes": 8,
  "stage_warn_days": { "await": 14, "partial": 5, "compare": 1, "adj": 7 }
}
```

To open it, go to a project, then its Applications menu, then **Task Admin Console (harness)**. The project you open it from is selected first.

## What it does
| View | Data | Notes |
|---|---|---|
| Rail | `GET /api/tasks/reader`, `GET /api/projects`, `GET /api/roles`, `GET /api/projects/{id}` | Lists projects that have at least one reader task **and** where this account holds `tasks_assign` (or is a site admin). With view-only rights the API returns just your own tasks, so a dashboard there would mislead. Protocols are listed under each project. Collapsible, showing the Flywheel mark when collapsed. |
| Overview | tasks | KPIs, a status donut, throughput against the last due date, a projected finish at the 14-day pace, and a "Needs attention" list (overdue by reader, pace outliers, adjudication blocked after reads are in, stalled drafts, unassigned reads). |
| Workflow | tasks (reads + adjudication tasks on the same container) | Stages each case: awaiting reads → some reads in → waiting on comparison → adjudicating → final (no adjudication / adjudicated). Shows time in stage, gap between reads, adjudication rate and turnaround. |
| Readers | tasks (`transitions`) | Workload bars, a strip of read times (in progress → completed), a sortable table, and a reader drawer with **Reassign not-started reads**. |
| Cases | tasks | One row per container, with a drawer listing every task on it, **Open in viewer** and **Reassign**. |
| Exports | `GET /api/reports`, `POST /api/{type}/reports`, `GET …/reports/{id}/csv`, `DELETE …/reports/{id}` | Uses the platform's **Task Reports Queue** (the same queue as the project's *Task Report Queue* tab). Queues a *Forms and annotations* and/or *Task details* report for the selected protocol, tracks it (queued → building → ready), downloads the CSV, deletes old reports, and shows "N tasks completed since this report". |
| Diagnostics | — | Every call made, which columns the server accepted, the `subcategory` values seen, and one raw task. |

The only things it writes are **reassign** (`PUT /api/tasks/reader/{id}/assign`, the same call the Reader Shell's Claim uses) and **task reports** (queue and delete, through the platform's report queue).

## What the spike learns (check Diagnostics)
1. Does an admin's `GET /api/tasks/reader` return every task on the project, including other readers' and blocked adjudication tasks? Which extra columns are accepted at a full page size?
2. **How are adjudication tasks marked?** The harness checks `adjudication`, then `subcategory`, then the protocol label (see the `subcategory values` line). It also assumes these statuses (VERIFY):
   - `blocked`: waiting for the platform's comparison.
   - `cancelled`: the reads agreed.
   - `todo` / `in_progress`: adjudicating.
   - `completed`: resolved.
3. `GET /api/users`: is it allowed for this role? If not, names fall back to short IDs. A project-permissions lookup is the next fallback.
4. Reassign: does `PUT …/assign` work for an admin on someone else's task? Does it appear in the task history?
5. Task Reports Queue (read from the core 23.x web app; VERIFY live):
   - **List:** `GET /api/reports?project_id=…&sort=created:desc`. Records carry `report_type`, `protocol_id`, `status` (`pending` / `in_progress` / `completed` / `failed` / `canceled`), `created` and `size`.
   - **Queue:** `POST /api/{form_and_annotation|task_detail}/reports` with `{protocol_id, project_id, version, metadata_columns}`. The core UI sends a fixed column list, and the harness sends the same one.
   - **Download:** `GET /api/{type}/reports/{id}/csv`. Core sends `Accept: text/csv`, which the SDK proxy can't set; check that the proxy returns the CSV text.
   - **Delete:** `DELETE /api/{type}/reports/{id}`.
   - **Permissions:** `tasks_report_read`, `tasks_report_create` and `tasks_report_delete`, behind the core feature flag `tasks_refactor`.

## Path to production (same pattern as the Reader Shell)
This harness is the spike tool. The product follows the deployment pattern the Reader Shell settled on, taken from the Uploader and the Data Contributor Dashboard (MR !620 docs build):
- **Its own address on the customer's Flywheel site, not an extension iframe.** Target: `https://<site>/reading-ops/`. Avoid `/admin`, which reads as core site administration. It's an nginx location with `try_files` falling back to the app's `index.html`, in the same Helm component as `/reader/` (`tags: reading: true`) or its own tag.
- **Sign-in:** the Uploader's pattern unchanged. It uses `@auth0/auth0-angular` (PKCE) against the same Auth0 app as core, reads its config from `GET /api/config`, and gets a token silently from the existing Auth0 session. A guard on every route sends signed-out users through the standard login, and an interceptor adds the Bearer token to `/api/*` calls. Add `https://<site>/reading-ops` to Auth0's allowed callback URLs.
- **Identity:** the signed-in user comes from `GET /api/users/self`, never the Auth0 profile, because a task's `assignee.id` is the Flywheel user ID.
- **No mock-data fallback in production builds.** This harness's `#demo` mode is a development tool only, and an outage must look like an outage.
- **One codebase with the Reader Shell:** one Angular workspace with a shared library for sign-in, config, the reader-tasks API (column list, stable sort, paging, refresh), the task model and the dark `@flywheel-io/vision` theme. It builds two apps, `reader` and `reading-ops`. The Data Contributor Dashboard should share the same starter.
- **Who gets it:** users with `tasks_assign` on at least one project, and site admins. There's no forced redirect: a "Task admin" link from core and from Task Manager is enough. The reader-role redirect stays as specified for `/reader/`.
- **Downloads get easier:** on the site's own address, export files download with a normal authenticated fetch. The iframe download problem goes away.

Platform asks that affect this app:
- **Strip unblinding fields only for readers.** The reader shell's P0 removes `parent_ref.label`, `parent_details` and the creator name from reader responses. That has to depend on the caller (keep them for `tasks_assign` holders), or the admin console loses case labels.
- **Same-case independence (RS-T7 / RS-T8):** the server blocks a second read or self-adjudication. This console's Workflow tab should also flag any case where one person holds two of its tasks.
- **The `/api/tasks/reader` paging bug and the combined-column 500:** the same fixes the reader shell needs.

## Not in this harness yet
- **Agreement between reads and the answers matrix:** these need form responses per task (the form-responses page model in SDK 23). This is the next step.
- **Queries and notifications:** these are product concepts (late 2026 and 2027) with no API yet; they stay in the design prototype.
- **Coded reader names:** the toggle is display-only, and task reports list assignees as stored.

## Related
- Design prototype canvas: "Task Admin Console" (claude.ai artifact)
- Reader app: `reader-shell-harness`
- Notes: Custom Apps project → `task-admin-console-notes.md`
