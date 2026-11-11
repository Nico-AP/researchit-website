<p align="center">
  <img src="researchit/core/static/core/img/logo/rit_logo.svg" alt="Pfiffner Research IT" width="420" />
</p>

# researchit-website

The website of **Pfiffner Research it** ([pfiffner-researchit.com](https://pfiffner-researchit.com)).
It is a one-page Django site whose content is managed in [Wagtail](https://wagtail.org) at
`/cms/`. CI ships it as a Docker image to `ghcr.io/nico-ap/researchit-website`.

| Path                      | What                                                            |
|---------------------------|-----------------------------------------------------------------|
| `config/settings/`        | `base.py` (shared), `local.py` (dev), `production.py` (image)   |
| `researchit/website/`     | Wagtail page models, templates, migrations, tests               |
| `researchit/core/`        | custom user model, static files (CSS/JS/images), SCSS sources   |
| `.sass/`                  | npm setup for compiling the SCSS                                |
| `Dockerfile`              | production image (uv, gunicorn, whitenoise, non-root)           |
| `.github/workflows/`      | build, test and push the image; prune old images                |

---

## Development setup

You need [uv](https://docs.astral.sh/uv/) and, only for changing styles, Node.js. Docker is
optional and only used to test the production image.

```bash
uv sync                          # Python 3.12 + all deps (incl. dev) into .venv
cp .env.example .env             # local settings; set any DJANGO_SECRET_KEY
uv run pre-commit install        # lint/format/audit hooks on every commit
uv run python manage.py migrate  # SQLite db.sqlite3; also seeds the CMS content
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

- Site: <http://localhost:8000/>
- CMS (Wagtail): <http://localhost:8000/cms/>
- Django admin (users): <http://localhost:8000/admin/>

`manage.py` uses `config.settings.local`: `DEBUG` from `.env`, SQLite, debug toolbar,
console e-mail, and log files in `logs/`.

### Two-factor authentication

Every user with admin access (CMS or Django admin) needs a second factor: a TOTP code
from an authenticator app.

Recovery route:

  ```bash
  uv run python manage.py reset_2fa <username>   # locally
  just manage reset_2fa <username>               # production, from researchit-deploy
  ```

### Styles

The CSS is compiled from `researchit/core/assets/scss/` into
`researchit/core/static/core/css/researchit.css`. The compiled file is committed, so commit
it together with the SCSS change.

```bash
cd .sass && npm install
npm run sass:watch   # while developing
npm run sass:build   # minified build before committing
```

### Dependencies

```bash
uv add <package>==<version>      # runtime dependency (pin exact versions)
uv add --dev <package>           # dev-only tool
uv lock --upgrade-package django # bump one package
```

The pre-commit hooks keep `uv.lock` in sync and run `pip-audit` on the runtime
dependencies.

---

## Testing

```bash
uv run python manage.py test     # unit tests (fresh DB, runs all migrations)
uv run coverage run manage.py test && uv run coverage report
uv run pre-commit run --all-files  # ruff, djLint, uv-lock, pip-audit, ...
```

The tests are in `researchit/website/test.py`. They check the seeded content, the
settings-driven contact details, standard pages and the footer, and the 404 page. They pass
with local and with production settings.

### Testing the production image

CI runs these checks on every PR. Run them locally before a release if you changed
settings, dependencies or the Dockerfile:

```bash
docker build -t researchit-website:dev .

# Django's deployment checklist with production settings
docker run --rm -e DJANGO_SECRET_KEY=$(openssl rand -hex 32) -e DJANGO_ALLOWED_HOSTS=example.com \
  -e DATABASE_URL=sqlite:////tmp/t.sqlite3 researchit-website:dev \
  python manage.py check --deploy --fail-level WARNING

# Tests inside the image
docker run --rm -e DJANGO_SECRET_KEY=$(openssl rand -hex 32) -e DJANGO_ALLOWED_HOSTS=testserver \
  -e DATABASE_URL=sqlite:////tmp/t.sqlite3 researchit-website:dev python manage.py test
```

To test the whole stack (Postgres, Caddy, media serving), use the staging VM from
researchit-deploy (`just env=staging ...`).

---

## Release guide

Releases are git tags. Each tag builds an image that stays in GHCR for good, and the
server only runs images whose version is pinned in researchit-deploy.

| Event               | Image tags pushed                  | Kept in GHCR        |
|---------------------|------------------------------------|---------------------|
| PR to `main`        | none (build + checks only)         | –                   |
| push to `main`      | `:main`, `:sha-<short>`            | newest 3            |
| tag `v1.2.3`        | `:1.2.3`, `:1.2`                   | forever             |

### 1. Prepare

Work on `dev`. Before releasing:

- tests and `pre-commit run --all-files` pass
- model changes have their migrations committed
- if styles changed, `researchit.css` was rebuilt and committed

### 2. Merge and tag

Open a PR from `dev` to `main`. CI builds the image and runs the deploy checks, tests and
smoke render. Merge once it's green, then tag the merge commit
([semver](https://semver.org): patch for fixes, minor for features, major for breaking
changes such as a migration that drops data):

```bash
git switch main && git pull
git tag -a v1.2.3 -m "v1.2.3"
git push origin v1.2.3
```

Wait for the `docker` workflow run of the tag to finish. The image is then
`ghcr.io/nico-ap/researchit-website:1.2.3`.
