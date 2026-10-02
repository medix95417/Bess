# Editing the site

1. Open `/editor/` and sign in.
2. Choose **Add a record**. Select Page, Incident, Document, Question, Update, or Meeting.
3. Enter a title, short summary, and body. Use a blank line between paragraphs. A paragraph beginning `## ` becomes a heading. HTML is escaped.
4. Leave the status at **Draft**. Add evidence labels and an actual review date. Save, then use **Preview page**.
5. Add source records in **Sources**: publisher, URL, source type, publication date when known, and date checked. Attach sources in the entry's citation rows and describe which claims they support.
6. A publisher reviews the entry and selects **Published**. A future publication time keeps it private until that time. Publication does not require a server restart.

## Adding an incident

Fill in date, location, country, manufacturer/integrator, battery chemistry, event type, impacts, and comparison limits. Leave unknown facts blank; the public page says when they are not established. Latitude/longitude are optional and must be provided together. Use locality coordinates unless exact site coordinates are verified. Explain approximate placement.

Use a separate entry for a distinct later event at the same facility. Do not combine dates or assume every incident at one location involves the same equipment. A count on the page is the count of selected published cases, not a total number of all incidents.

## Documents and privacy

Upload PDFs up to 20 MB, or link to the original source. PDFs are served as downloads, not executable page content. Check files and remove personal details before uploading. File type checks are not malware scanning; accept files only from trusted editors and sources.

Draft PDFs are private. Their download link works only with an authorized staff preview. A published record's PDF is public. Changing that record back to Draft removes public download access. Removed/replaced files remain in storage for revision recovery and backup; periodic retention review is an administrator task.

## Questions and meetings

Questions start at **Open question**. Change to **Response requested** only after an actual request. Attribute written responses and cite the supporting document. A blank response means this site has no published response, not that an organization refused to respond.

Meetings need an event date to publish. Add the local New York time, full venue, and source announcement. Keep past meetings as part of the record. No fictional meeting dates are seeded.

## Users and permissions

A superuser creates accounts in `/admin/auth/user/`. Check **Staff status** and assign either:

- **Contributors:** prepare and edit unpublished records and attach existing sources. Cannot publish or edit a published entry.
- **Publishers:** review and publish content, add/edit sources, and restore revisions. Cannot manage user accounts or delete entries by default.

Only give superuser status to the site administrator. The built-in groups are reset by `seed_content`; disable automatic seeding after initial setup if customizing permissions. Password reset by email is not configured; an administrator can use `docker compose exec web python manage.py changepassword USERNAME`.

## Corrections and history

Enter a public change note for a material correction. Entry saves through the admin store a revision snapshot, including citation links. In **Revisions**, inspect earlier versions or choose **Restore as draft**. Restoration requires a publisher and a confirmation POST, saves the current version first, and removes the entry from public view until republished.

Source records have the standard Django admin audit log, not full restorable snapshots. If a source materially changes, create a new source record to preserve the old attribution; add an editorial note to affected entries.

## Before launch

Complete Site settings with the operator name and contact email. Update the About page's operator paragraph. Review every public page. Attach and reconcile the original local filings before changing local claims to Documented. Confirm public hosting settings with the deployment guide.
