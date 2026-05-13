# terraform-gcs-rum-counter

[![Python](https://img.shields.io/badge/python-3.9+-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Terraform](https://img.shields.io/badge/terraform-statefiles-purple)](https://developer.hashicorp.com/terraform)
[![GCS](https://img.shields.io/badge/google-cloud_storage-orange)](https://cloud.google.com/storage)

A lightweight Python CLI that scans Terraform state files stored in Google Cloud Storage (GCS) and estimates your **Terraform managed resource (RUM)** counts, helping you understand potential [HCP Terraform billing](https://developer.hashicorp.com/terraform/cloud-docs/overview/estimate-hcp-terraform-cost) before you get a surprise invoice.

> 📖 **Background:** Read the full write-up on Medium — [How I Built a Tool to Estimate Terraform Managed Resource Costs Before They Hit Your Bill](https://medium.com/@kevinmya/how-i-built-a-tool-to-estimate-terraform-managed-resource-costs-before-they-hit-your-bill-f634c613a84c)

---

## Table of Contents

- [Why This Tool](#why-this-tool)
- [How It Works](#how-it-works)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
- [CLI Reference](#cli-reference)
- [Output](#output)
- [Resource Counting Logic](#resource-counting-logic)
- [Disclaimer](#disclaimer)
- [License](#license)

---

## Why This Tool

If you’ve ever migrated to HCP Terraform (formerly Terraform Cloud) or been hit with an unexpected bill, you know the pain: you don’t really know how many **"managed resources"** you have until it’s too late.

The problem? You might have dozens of `.tfstate` files scattered across a Google Cloud Storage bucket, and there's no easy out of the box way to audit them all and get a total count before committing to a plan.

HashiCorp bills Terraform Cloud by the number of managed resources under management **(RUM)**. Not all resources in your state file count, `data` sources and `null_resource` blocks are excluded. This tool automates that distinction across an entire GCS bucket, giving you a per-state-file breakdown and a grand total.

---

## How It Works

1. Connects to GCS using your application default credentials
2. Recursively lists all `.tfstate` files in a bucket (optionally filtered by prefix)
3. Parses each state file and categorizes every resource as **Billable RUM**, **Data RS**, or **Null RS**
4. Prints a summary table to stdout and saves a report to `project/<project_id>.txt`

---

## Prerequisites

- Python 3.9+
- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) (`gcloud`)
- GCS read access on the target bucket (`roles/storage.objectViewer` or equivalent)

Authenticate your local environment:

```bash
gcloud auth application-default login
```

Verify bucket access:

```bash
gcloud storage ls gs://YOUR_BUCKET/
```

---

## Installation

```bash
git clone https://github.com/kevinmya/terraform-gcs-rum-counter.git
cd terraform-gcs-rum-counter
pip install -r requirements.txt
```

---

## Quick Start

```bash
python3 terraform_gcs_rum_counter.py \
  --project my-gcp-project \
  --bucket my-terraform-state-bucket
```

That's it. Results are printed to the terminal and saved to `project/my-gcp-project.txt`.

---

## Usage

### Scan an entire bucket

```bash
python3 terraform_gcs_rum_counter.py \
  --project my-gcp-project \
  --bucket my-terraform-state-bucket
```

### Scan a specific folder / prefix

```bash
python3 terraform_gcs_rum_counter.py \
  --project my-gcp-project \
  --bucket my-terraform-state-bucket \
  --prefix product/team-a/
```

### Verbose per-file output

```bash
python3 terraform_gcs_rum_counter.py \
  --project my-gcp-project \
  --bucket my-terraform-state-bucket \
  --verbose
```

### Adjust log level

```bash
python3 terraform_gcs_rum_counter.py \
  --project my-gcp-project \
  --bucket my-terraform-state-bucket \
  --log-level DEBUG
```

---

## CLI Reference

| Flag | Short | Required | Default | Description |
|------|-------|----------|---------|-------------|
| `--bucket` | `-b` | ✅ | — | GCS bucket name |
| `--project` | — | ❌ | ADC default | GCP project ID |
| `--prefix` | `-p` | ❌ | `""` (root) | GCS prefix / folder to scan |
| `--verbose` | `-v` | ❌ | `false` | Print per-file resource counts |
| `--log-level` | `-l` | ❌ | `WARNING` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) |

---

## Output

### Terminal

![CLI example output](https://github.com/kevinmya/terraform-gcs-rum-counter/raw/main/docs/example-output.png)

### Report file

Results are saved automatically to:

```
project/<project_id>.txt
```

If no `--project` is provided, the file is saved as `project/default-project.txt`.

---

## Resource Counting Logic

Resources in each `.tfstate` file are categorized using the following rules:

| Category | Condition | Counts toward billing? |
|----------|-----------|------------------------|
| **Billable RUM** | `mode != "data"` and `type != "null_resource"` | ✅ Yes |
| **Data RS** | `mode == "data"` | ❌ No |
| **Null RS** | `type == "null_resource"` | ❌ No |

**Examples:**

```hcl
# → Billable RUM
resource "google_compute_instance" "vm" {}

# → Data RS
data "google_client_config" "current" {}

# → Null RS
resource "null_resource" "setup" {}
```

> **Note:** Instance counts are used, not resource block counts. A resource block with `count = 3` or `for_each` across 3 keys contributes 3 to the total.

---

## Disclaimer

This tool provides an **estimated** Terraform managed resource count. It is not an official HashiCorp licensing calculator. Actual HCP Terraform / Terraform Cloud billing may vary depending on your plan, billing model, discounts, and enterprise agreements.

This project is not affiliated with or endorsed by HashiCorp.

---

## License

[MIT](LICENSE)
