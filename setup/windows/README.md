# Windows Setup

Use this folder only on a Windows PC.

Before installing, CleanMol needs Python 3.10 or newer and Node.js 20.9 or newer. If either is missing, `1-install-windows.bat` will stop and tell you what to install.

## What To Click

1. Double-click `1-install-windows.bat`
2. Double-click `2-run-windows.bat`
3. Double-click `3-end-windows.bat` when you are finished
4. Optional: double-click `4-install-advanced-discovery-pack.bat` only if you need Chemprop/advanced modeling

## What Each File Does

- `1-install-windows.bat`: installs CleanMol's Python and frontend dependencies
- `2-run-windows.bat`: starts the local CleanMol app and opens it in your browser
- `3-end-windows.bat`: stops the local CleanMol servers
- `4-install-advanced-discovery-pack.bat`: optional advanced setup in a separate environment

CleanMol Core works without the optional advanced pack. Chemprop support is scaffolded but not active CleanMol scoring in this public preview. If advanced setup fails, normal CleanMol discovery still uses RDKit Morgan fingerprint baseline and heuristic triage scoring.

## Default Folders

The installer creates:

```text
C:\Users\YourName\CleanMol\input
C:\Users\YourName\CleanMol\output
```

Put PDFs in the input folder. Save results in the output folder.

## If Something Feels Confusing

Use this order again:

```text
1-install-windows.bat
2-run-windows.bat
3-end-windows.bat
```

You do not need to open the `cleanmol` code folder to run the app.
