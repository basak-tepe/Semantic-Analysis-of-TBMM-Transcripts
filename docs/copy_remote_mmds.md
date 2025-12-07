from Parent folder (for removing unnecessary files)

> find . -maxdepth 2 -type f -name "*.txt" -delete
> find . -maxdepth 2 -type f -name "*.idx" -delete


copy the ocr folder of remote 


# exclude everyting except folders and result.mmd

## change for the term-year you want 

rsync -avz --progress \
  --include="d22-y1_TXTs/" \
  --include="d22-y1_TXTs/*/" \
  --include="d22-y1_TXTs/*/result.mmd" \
  --exclude="*" \
  cronus-basak:/home/tepe/deepseek/TPT/OCR/ .


