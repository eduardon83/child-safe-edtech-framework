# Text admin for CSEF and HDSF

A small web page to edit the information text of both frameworks, without code.

- Sign in with email and password.
- Pick CSEF or HDSF, then a file.
- Change the text and press **Save and publish**.

Each save is a commit to `main`. A GitHub workflow then rebuilds the site. The change is live in about 2 to 4 minutes. To undo a change, revert its commit on GitHub (the admin links to each file's history).

## What you can edit

| Kind | Files | How it looks |
| --- | --- | --- |
| Guides | `README.md`, `framework/*.md` | The whole Markdown file, with a preview |
| Rules and sources | `rules.yaml`, `sources.yaml`, `watch.yaml` | One box per text: title, what to do, why, how to improve, status, notes |
| Packs | `packs/*.yaml` | The texts of each pack rule and source |
| Page text | `tooling/*.template.html` | One box per paragraph, heading or list item |
| CSEF only | Literacy Compass targets, serious-game criteria, the questionnaire and its translations | One box per text |

Not editable here: buttons and their labels, form labels, ids, levels, severities, checks, patterns, links in YAML and anything the build generates (such as `legislation.md` in HDSF or the catalogue pages). Change those through a pull request.

The admin keeps the rest of each file exactly as it was. In page text you can use simple tags: `<a>`, `<strong>`, `<em>`, `<code>`. Keep any `{placeholder}`, because the build fills it in.

The admin warns about em dashes, double spaces and very long sentences. HDSF also runs its style check (`STYLE.md`) when it rebuilds. If that check fails, the site does not update; the admin links to the reason. Fix the text and save again.

## Set it up (once)

You need a Cloudflare account (the free plan works) and Node.js 20 or later on your computer.

### 1. Make a GitHub token

On GitHub: **Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**.

- Repository access: **Only select repositories**: `child-safe-edtech-framework` and `digital-health-safety-framework`.
- Permissions: **Contents: Read and write**, **Actions: Read-only**.
- Expiry: the longest you are comfortable with. Put a reminder in your calendar to renew it.

Copy the token. You need it in step 3.

### 2. Install and sign in to Cloudflare

```sh
cd admin
npm install
npx wrangler login
```

### 3. Add the secrets

```sh
npx wrangler secret put GITHUB_TOKEN          # paste the token from step 1
openssl rand -base64 48 | npx wrangler secret put SESSION_SECRET
```

### 4. Add yourself as an editor

```sh
node tools/add-editor.mjs                     # on the Workers Paid plan
node tools/add-editor.mjs --free-plan         # on the Workers Free plan
npx wrangler secret put EDITORS < editors.json
```

The tool asks for your email, your name and a password of at least 12 characters. It stores only a hash, in `editors.json` on your computer. That file is never committed. Run it again to add more people or to change a password. Remove someone with `node tools/add-editor.mjs --remove their@email`, then send `editors.json` again.

Use `--free-plan` on the Workers Free plan. It makes a lighter hash that fits the free CPU limit of 10 ms per request.

### 5. Publish

```sh
npx wrangler deploy
```

Wrangler prints the address, for example `https://framework-text-admin.<your-account>.workers.dev`. Open it and sign in.

To use `admin.kendirstudios.pt` instead, the `kendirstudios.pt` domain must be in your Cloudflare account. Then remove the `#` in front of `routes` in `wrangler.toml` and deploy again.

## Security

- Passwords are hashed with PBKDF2-SHA256. Only the hashes are stored, as a Cloudflare secret.
- The session is a signed cookie (HttpOnly, Secure, SameSite=Strict) that lasts 12 hours. Removing someone from `EDITORS` ends their sessions at once.
- Sign-in attempts are limited to 5 per minute for each address and email.
- The GitHub token never leaves Cloudflare. It can write only to the two repositories.
- The Worker refuses any file or field that is not on the list in `src/sites.js`, and any change to a file that changed since you opened it.
- There is no two-step sign-in. Use a long password that you use nowhere else.

## For developers

```sh
npm test                                      # unit tests, with a fake GitHub
node test/dev-server.mjs /tmp/csef-copy /tmp/hdsf-copy   # local run on http://localhost:8787
```

The local run edits the folders you pass in. Use copies. Sign in with `admin@example.org` and `correct horse battery`.

What is editable lives in `src/sites.js`. The rebuild is `.github/workflows/rebuild-after-edit.yml` in each repository. CI skips commits that start with `admin:`, because the rebuild runs the same checks.
