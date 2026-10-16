# Publish this Git repository to GitHub

The game has already been initialized and committed locally on the `main` branch.

1. On GitHub, create an **empty** repository named `raftbound` under `hungtvb`. Do **not** initialize it with a README, .gitignore or license; these files already exist.
2. Open a terminal in this extracted `raftbound/` directory and run:

```bash
git remote add origin https://github.com/hungtvb/raftbound.git
git push -u origin main
```

GitHub will require authentication (credential manager or personal access token).

Once published, GitHub Actions runs the game tests automatically.

**This archive is a local, committed Git repository. It has not been pushed remotely.**
