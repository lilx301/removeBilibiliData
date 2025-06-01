echo $1
git status

git config user.name "github-actions[bot]"
git config user.email "githubci"
git status
git add .
git diff --cached --quiet || git commit -m "$1 $(date +"%Y-%m-%d %H:%M:%S %z") [ci skip]"
git push origin HEAD:master