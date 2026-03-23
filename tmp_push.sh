#!/bin/bash
cd /mnt/f/cloudsecurity
git add -A
git commit --amend --no-edit
git pull --rebase origin main
git push origin main
rm -f tmp_push.sh
