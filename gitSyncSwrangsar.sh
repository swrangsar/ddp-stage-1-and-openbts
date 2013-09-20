#!/bin/bash


git add --all .
git commit -am "commit at $(date +%Y%m%d%H%M%S)"
echo "...pulling..."
git pull
echo "...pushing..."
git push -u origin master