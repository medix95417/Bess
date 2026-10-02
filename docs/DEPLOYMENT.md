# Deployment and operations

## First start

Follow the README. The Compose configuration binds to `127.0.0.1:8080` by default so the first review stays on the host. The container runs as UID/GID 10001, with a read-only application filesystem. SQLite, sessions, uploads, and the login-throttle cache live in the `bess-data` volume.

Docker creates a new named volume using the `/data` directory ownership from the image. If reusing an existing volume, ensure UID 10001 can write it. Do not use `docker compose down -v` unless you intentionally want to delete the database and documents.

## Public HTTPS

Put an HTTPS reverse proxy in front of port 8080. For a host-based proxy, retain the loopback binding. Set `.env`:

```dotenv
ALLOWED_HOSTS=your-domain.example,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://your-domain.example
HTTPS=true
TRUST_PROXY=true
DEBUG=false
SEED_CONTENT=false
```

The proxy must preserve `Host`, forward to `http://127.0.0.1:8080`, and **overwrite** `X-Forwarded-Proto` with `https`. Do not enable `TRUST_PROXY` when untrusted clients can directly supply that header to the application. Keep the internal port inaccessible from the public internet. Keep `127.0.0.1` in ALLOWED_HOSTS for the health check.

Example Caddy configuration on the host:

```caddy
your-domain.example {
    request_body {
        max_size 22MB
    }
    reverse_proxy 127.0.0.1:8080 {
        header_up X-Forwarded-Proto https
    }
}
```

Configure DNS and obtain a valid TLS certificate through your hosting/proxy setup. This repository does not purchase a domain or deploy a public server. Check your proxy's current documentation when installing it.

Apply configuration with `docker compose up -d --force-recreate`. Verify HTTPS, sign-in, static files, PDF uploads, and the incident map. Run `docker compose exec web python manage.py check --deploy` after configuring HTTPS. Proxy request-size limits should be at least 22 MB to allow the 20 MB PDF limit plus form overhead.

The application includes per-account failed-login throttling. A public deployment should also apply proxy-level request limiting; accounts remain subject to denial-of-service attempts. Add centralized logging or authentication controls if the deployment's needs grow.

## Back up

Pause editing while the backup runs so database and PDF state agree. The database snapshot uses SQLite's backup API and can be taken while public reads continue.

```sh
mkdir -p backups
docker compose exec web python manage.py backup_site --output /tmp/site-backup.tar.gz
docker compose cp web:/tmp/site-backup.tar.gz ./backups/site-backup.tar.gz
docker compose exec web rm /tmp/site-backup.tar.gz
```

Use a fresh filename each time, keep archives outside the repository, restrict access, and copy them off-host. They contain account password hashes, drafts, and uploaded documents. Save `.env` securely and separately; it is not included in the archive. A GitHub source push does not back up the live content.

## Restore safely

Restore into a **new, empty named volume**, preserving the original until verification. The command refuses to overwrite an existing database or uploads directory.

```sh
docker compose stop web
docker volume create bess-restored
docker run --rm --user 0 --entrypoint sh -v bess-restored:/data woodlawn-bess:local -c 'chown 10001:10001 /data'
docker run --rm --env-file .env --entrypoint python -v bess-restored:/data -v "$PWD/backups:/restore:ro" woodlawn-bess:local manage.py restore_site /restore/site-backup.tar.gz
```

Use a Compose override or update the volume definition to point `bess-data` to the external volume named `bess-restored`. Restart, verify records/accounts/downloads, and retain the old volume until satisfied. The restore command intentionally bypasses the normal startup entrypoint so migrations do not create a database before restoration.

## Update code

Back up first, then:

```sh
git pull --ff-only
docker compose up --build -d
docker compose logs --tail=100 web
```

Migrations run automatically on startup. Test updates on a restored copy before applying significant schema changes. Keep application code and Python dependencies up to date. Pin the base-image digest under your own release process if reproducible image provenance is required.

## Operational limits

- Single-host, single-instance SQLite design; not a multi-replica deployment.
- No automatic fact-checking, portal polling, email notifications, or account reset email.
- Server-side publication time is supported; changes become public on the next request after that time.
- Public page/source content is escaped. Trusted administrators still control what they publish and upload.
- Health endpoint `/healthz/` checks database access. It does not verify external source links or map-tile availability.
