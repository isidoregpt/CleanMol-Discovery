# Mac Setup

Use this folder only on an Apple Mac, including M-Series Macs.

Before installing, CleanMol needs Python 3.10 or newer and Node.js 20.9 or newer. If either is missing, `1-install-mac.command` will stop and tell you what to install.

## What To Run

Open Terminal in this `setup/mac` folder, then run:

```bash
chmod +x 1-install-mac.command 2-run-mac.command 3-end-mac.command
./1-install-mac.command
./2-run-mac.command
```

When you are finished:

```bash
./3-end-mac.command
```

## What Each File Does

- `1-install-mac.command`: installs CleanMol's Python and frontend dependencies
- `2-run-mac.command`: starts the local CleanMol app and opens it in your browser
- `3-end-mac.command`: stops the local CleanMol servers

## Default Folders

The installer creates:

```text
/Users/YourName/CleanMol/input
/Users/YourName/CleanMol/output
```

Put PDFs in the input folder. Save results in the output folder.

## If Something Feels Confusing

Use this order again:

```text
1-install-mac.command
2-run-mac.command
3-end-mac.command
```

You do not need to open the `cleanmol` code folder to run the app.
