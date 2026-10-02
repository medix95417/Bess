# Build validation — October 2, 2026

Completed in the development workspace:

- 14 Django tests covering public routes, filtering, draft and future-publication privacy, contributor/publisher permissions, citation requirements, private PDF delivery, file validation, escaped content, CSRF, login throttling, revision restore, idempotent seeding, and database backup contents.
- Migration consistency check and static asset compilation.
- Browser checks using Chromium at 1440px desktop and 390px mobile widths. Checked homepage, incident list/detail, documents, and questions for mobile overflow. No horizontal overflow or JavaScript exceptions were observed.
- Incident filter and map initialization; mobile menu interaction.
- Screenshots visually inspected and included under `docs/images`.

Docker is not installed in the development workspace. The image and Compose startup/restart checks are configured in `.github/workflows/ci.yml` for GitHub Actions. Check that workflow's result before treating container execution as verified. These checks do not establish that external source links will remain available or that the live permit record is current.

This is a runnable first edition with selected research, not a complete ingestion of all prior project files or all BESS incidents. Local source review remains in the private editorial queue.
