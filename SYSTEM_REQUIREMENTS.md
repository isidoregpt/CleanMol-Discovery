# System Requirements

## Supported Operating Systems

- Windows 10 or newer
- Windows 11
- macOS on Apple Silicon / M-Series Macs

## Core Requirements

- Python 3.11 recommended
- Node.js 20 or newer recommended
- 8 GB RAM minimum for small demo/testing
- 16 GB RAM recommended for ordinary PDF and discovery workflows
- local disk space for PDFs, extracted markdown, CSV, Excel, and JSON outputs

## Demo Runtime

The synthetic public demo should complete quickly because it copies a small prepared packet and requires no API keys.

## Typical Runtime Guidance

Ten born-digital PDFs may take minutes to longer depending on PDF length, figure count, provider latency, and API limits.

## API Cost Warning

LLM extraction uses external provider APIs when keys are provided. Provider billing, rate limits, and data-use terms are controlled by those providers.

## Scanned PDF Limitation

CleanMol is designed primarily for born-digital PDFs. Scanned PDFs may need OCR before use.

## Optional Advanced Pack Caveats

Chemprop v2, REINVENT 4, and FairChem/UMA are optional and may require heavier dependencies, separate environments, GPUs, or expert configuration. They are not part of the default CleanMol Core install.
