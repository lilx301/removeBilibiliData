#!/bin/bash
git add .
git commit -m "$(date +"%Y-%m-%d %H:%M:%S")"
git push origin || True
git push berg || True
git push vs  || True