# Upload To GitHub

This folder is ready to push as a GitHub repository.

## Option 1: GitHub Desktop

1. Open GitHub Desktop.
2. Choose `File > Add local repository`.
3. Select `D:\You\Documents\codex\nepsgit_github_repo`.
4. Click `Publish repository`.
5. Choose `Private` unless you are sure you want it public.

## Option 2: Command Line

Create an empty GitHub repository first, then run:

```powershell
cd D:\You\Documents\codex\nepsgit_github_repo
git remote add origin https://github.com/YOUR-USERNAME/nepsgit.git
git branch -M main
git push -u origin main
```

Replace `YOUR-USERNAME` with your GitHub username and replace `nepsgit` if you choose a different repository name.

## If GitHub CLI Is Installed

```powershell
cd D:\You\Documents\codex\nepsgit_github_repo
gh auth login
gh repo create nepsgit --private --source . --remote origin --push
```
