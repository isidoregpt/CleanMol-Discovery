# Troubleshooting

## Windows Install Fails

Use `setup/windows/1-install-windows.bat` from the `setup/windows` folder. Confirm Python and Node.js are installed and available in PATH.

## Mac Install Fails

Use `setup/mac/1-install-mac.command`. If macOS blocks the file, right-click it and choose Open.

## Python Version Problems

Use Python 3.11 where possible. Very old Python versions are not supported.

## Node or npm Problems

Install Node.js 20 or newer, then rerun the install script for your operating system.

## RDKit Install Issues

RDKit is part of CleanMol Core. If RDKit fails to install, CleanMol cannot perform the default SMILES validation or Morgan fingerprint baseline.

## Optional Chemprop Install Fails

The Advanced Discovery Pack is optional. If it fails, CleanMol Core still works and rankings use RDKit Morgan fingerprint baseline and heuristic triage scoring.

## Optional REINVENT Setup Fails

REINVENT 4 is optional. If it is missing or unconfigured, CleanMol uses the built-in rule-based hypothesis generator.

## API Key Errors

Check that the key is pasted into the correct field. Use `Clear saved keys` on shared machines before entering new keys.

## Hugging Face Errors

Some datasets require a Hugging Face token or may be temporarily unavailable. Discovery can still run with local data and built-in generation.

## Empty Output Folder

Confirm the output folder exists and is writable. For Discovery Automation, run `Run Synthetic Demo` first to confirm CleanMol can write files.

## Invalid PDF Extraction

Use born-digital PDFs when possible. Scanned PDFs may require OCR before CleanMol can extract useful text.

## Excel File Locked

Close the Excel workbook before rerunning CleanMol. Excel may lock open files.

## Localhost Port Conflict

If port 3000 is already in use, the run script will try another port. Use the exact URL printed by the script.
