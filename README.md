# L++ Package Registry

Canonical package registry for L++.

Production remote:

```text
git@github.com:samarnever-droid/llppregistry.git
```

The registry is git-backed and content-addressed:

```text
index/<sparse-package-path>   # per-package JSON index entries
blob/<sha256>                 # package artifacts named by SHA-256
registry/index.json           # generated public aggregate for website / Worker mirrors
```

Publishing is done by Keel, not by the Cloudflare Worker:

```bash
export KEEL_REGISTRY=git@github.com:samarnever-droid/llppregistry.git
keel check && keel test && keel verify
keel publish
```

`registry.lplusplus.bond` is a read-only HTTP mirror. Git push rights are the publisher authority.

## HTTP Mirror (Cloudflare Worker)

`registry-worker/` hosts the read-only HTTP mirror deployed to `registry.lplusplus.bond`.
It is automatically deployed via GitHub Actions when changes land in `main`.

Required GitHub Actions secrets:
- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`

