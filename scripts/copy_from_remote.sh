#!/bin/bash

for d in {17..22}; do
  for y in {1..5}; do
    folder="d${d}-y${y}_TXTs"

    echo "=== Checking $folder ==="

    # First check if folder exists on remote to avoid rsync error spam
    if ssh cronus-basak "[ -d /home/tepe/deepseek/TPT/OCR/${folder} ]"; then
      echo "Remote folder exists, syncing $folder ..."

      rsync -avz --progress \
        --include="${folder}/" \
        --include="${folder}/*/" \
        --include="${folder}/*/result.mmd" \
        --exclude="*" \
        cronus-basak:/home/tepe/deepseek/TPT/OCR/ .

    else
      echo "Skipping $folder (does not exist on remote)"
    fi

    echo
  done
done
