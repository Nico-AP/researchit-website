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

### Icons

[Bootstrap Icons](https://icons.getbootstrap.com/) are used as a font
(`<i class="bi bi-envelope" aria-hidden="true"></i>`), but the stylesheet only contains the
icons the site uses. To add one:

1. Find the icon on icons.getbootstrap.com; its page lists the Unicode codepoint (e.g. `U+F32F`).
2. Add it to `$bi-icons` in `researchit/core/assets/scss/vendors/bootstrap_icons_1-13-2/_bootstrap-icons.scss`,
   e.g. `"envelope": "\f32f",`.
3. Rebuild the CSS (`npm run sass:build`) and commit both files.

The font file already contains every icon, so nothing else needs downloading.

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
uv run pre-commit run --all-files  # ruff, djLint, uv-lock, ...
```

**CI** (`.github/workflows/test.yml`) runs on every push and pull request:
- **lint:** all pre-commit hooks, plus `pip-audit` on the production dependencies
- **test:** checks that no migrations are missing, then runs the tests against Postgres 18
  (the version the server uses), with coverage that must stay at or above 80%

### Testing the production image

The image is only built for release tags, and these checks run before it is pushed.
To catch problems before tagging, run them locally if you changed settings,
dependencies, static files or the Dockerfile:

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

Releases are git tags. Only a tag builds an image (`docker` workflow): `v1.2.3` pushes
`:1.2.3` and `:1.2`, which stay in GHCR for good. Pushes to branches and pull requests
run the `test` workflow only. The server only runs images whose version is pinned in
researchit-deploy.

### 1. Prepare

Work on `dev`. Before releasing:

- tests and `pre-commit run --all-files` pass
- model changes have their migrations committed
- if styles changed, `researchit.css` was rebuilt and committed

### 2. Merge and tag

Open a PR from `dev` to `main` and merge once the `test` workflow is green. If you
changed settings, dependencies or the Dockerfile, run the image checks above first.
Then tag the merge commit
([semver](https://semver.org): patch for fixes, minor for features, major for breaking
changes such as a migration that drops data):

```bash
git switch main && git pull
git tag -a v1.2.3 -m "v1.2.3"
git push origin v1.2.3
```

Wait for the `docker` workflow run of the tag to finish. It builds the image, runs the
deploy checks, tests and smoke render, and only then pushes
`ghcr.io/nico-ap/researchit-website:1.2.3`. If it fails, nothing is pushed: fix the
problem on `dev`, merge again and release the next patch version (don't move the tag).
