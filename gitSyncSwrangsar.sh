#!/bin/bash
git add *
git commit -am "commit at $(date +%Y%m%d%H%M%S)"
git pull
git push -u origin master
