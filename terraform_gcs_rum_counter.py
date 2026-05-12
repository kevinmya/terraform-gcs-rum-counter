#!/usr/bin/env python3

import argparse
import json
import logging
import os

from google.cloud import storage
import google.auth


##########################################
# Utility Functions
##########################################

def billable_categorization(resource):
    mode = resource.get("mode", "")
    resource_type = resource.get("type", "")

    if mode == "data":
        return "data"

    if resource_type == "null_resource":
        return "null"

    return "billable"


##########################################
# Logging
##########################################

def setup_logging(log_level):
    log_format = "%(levelname)s:%(asctime)s %(message)s"
    logging.basicConfig(format=log_format, level=log_level)


##########################################
# Arguments
##########################################

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Count billable Terraform resources from GCS Terraform state files."
    )

    parser.add_argument(
        "-b",
        "--bucket",
        required=True,
        help="GCS bucket name"
    )

    parser.add_argument(
        "-p",
        "--prefix",
        default="",
        help="Optional GCS prefix/folder to scan"
    )

    parser.add_argument(
        "--project",
        help="GCP project ID to use"
    )

    parser.add_argument(
        "-l",
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="WARNING",
        help="Set logging level"
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print detailed output"
    )

    return parser.parse_args()


##########################################
# Summary Formatter
##########################################

def generate_summary(rum_sum):
    grand_total = {
        'rum': 0,
        'null_rs': 0,
        'data_rs': 0,
        'total': 0
    }

    headers = [
        "State File",
        "Billable RUM",
        "Data RS",
        "Null RS",
        "Total"
    ]

    row_format = "{:<70}{:>15}{:>12}{:>12}{:>12}"

    output = []

    output.append("\n")
    output.append(row_format.format(*headers))
    output.append("-" * 125)

    for state in rum_sum:
        row = [
            state['name'],
            state['resources']['rum'],
            state['resources']['data_rs'],
            state['resources']['null_rs'],
            state['resources']['total']
        ]

        output.append(row_format.format(*row))

        grand_total['rum'] += state['resources']['rum']
        grand_total['null_rs'] += state['resources']['null_rs']
        grand_total['data_rs'] += state['resources']['data_rs']
        grand_total['total'] += state['resources']['total']

    output.append("-" * 125)

    output.append(
        row_format.format(
            "GRAND TOTAL",
            grand_total['rum'],
            grand_total['data_rs'],
            grand_total['null_rs'],
            grand_total['total']
        )
    )

    return "\n".join(output)


##########################################
# Write output to file
##########################################

def write_output(project_id, summary_text):
    output_dir = "project"

    os.makedirs(output_dir, exist_ok=True)

    if not project_id:
        project_id = "default-project"

    output_file = f"{output_dir}/{project_id}.txt"

    with open(output_file, "w") as f:
        f.write(summary_text)

    print(f"\nSaved output to: {output_file}")


##########################################
# Process GCS
##########################################

def process_gcs(bucket_name, prefix="", project_id=None, verbose=False):
    logging.info(
        f"Scanning bucket={bucket_name} "
        f"prefix={prefix} "
        f"project={project_id}"
    )

    if project_id:
        client = storage.Client(project=project_id)
    else:
        client = storage.Client()

    blobs = client.list_blobs(bucket_name, prefix=prefix)

    rum_sum = []

    for blob in blobs:
        blob_name = blob.name

        # Only process Terraform state files
        if not blob_name.endswith(".tfstate"):
            continue

        print(f"Processing: gs://{bucket_name}/{blob_name}")

        try:
            tfstate_contents = blob.download_as_text()

            state = json.loads(tfstate_contents)

            state_sum = {}
            state_sum['name'] = blob_name

            rum = 0
            null_rs = 0
            data_rs = 0

            resources = state.get("resources", [])

            for rs in resources:
                category = billable_categorization(rs)

                instances = len(rs.get("instances", []))

                if category == "null":
                    null_rs += instances

                elif category == "data":
                    data_rs += instances

                elif category == "billable":
                    rum += instances

                else:
                    logging.warning(
                        f"Unknown category={category} "
                        f"resource={rs.get('type')}"
                    )

            total = rum + null_rs + data_rs

            state_sum['resources'] = {
                'rum': rum,
                'null_rs': null_rs,
                'data_rs': data_rs,
                'total': total
            }

            rum_sum.append(state_sum)

            if verbose:
                print(
                    f"  billable={rum} "
                    f"data={data_rs} "
                    f"null={null_rs} "
                    f"total={total}"
                )

        except Exception as e:
            logging.error(
                f"Failed processing "
                f"gs://{bucket_name}/{blob_name}: {e}"
            )

    return rum_sum


##########################################
# Main
##########################################

def main():
    args = parse_arguments()

    setup_logging(args.log_level)

    try:
        credentials, detected_project = google.auth.default()

        if args.project:
            print(f"Using specified project: {args.project}")
        else:
            print(f"Using default project: {detected_project}")

    except Exception:
        detected_project = None

    active_project = args.project or detected_project

    rum_sum = process_gcs(
        bucket_name=args.bucket,
        prefix=args.prefix,
        project_id=args.project,
        verbose=args.verbose
    )

    summary_text = generate_summary(rum_sum)

    print(summary_text)

    write_output(active_project, summary_text)


if __name__ == "__main__":
    main()