param(
  [Parameter(Mandatory = $true)]
  [string]$ZipFileBase
)

python scripts/decompress_zip_file.py $ZipFileBase
exit $LASTEXITCODE
