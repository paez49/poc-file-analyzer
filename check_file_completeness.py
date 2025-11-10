import os
from typing import Set

import boto3
from colorama import Fore, Style, init


def list_s3_keys(client, bucket: str, prefix: str) -> Set[str]:
    """Return the set of keys currently stored in S3 under a prefix."""
    paginator = client.get_paginator("list_objects_v2")
    keys = set()
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            keys.add(obj["Key"])
    return keys


def get_base_name(key: str) -> str:
    """Extract base name from S3 key (without path and extension)."""
    filename = os.path.basename(key)
    # Remove .pdf, _pypdf.json, or _textract.json
    base = filename.replace(".pdf", "").replace("_pypdf.json", "").replace("_textract.json", "")
    return base


def check_processing_completeness(
    s3_client, 
    input_bucket: str, 
    output_bucket: str,
    input_prefix: str,
    output_prefix: str
) -> bool:
    """Check if all input files have corresponding output files."""
    
    # Get all input PDF files
    input_keys = list_s3_keys(s3_client, input_bucket, input_prefix)
    input_pdfs = {k for k in input_keys if k.endswith(".pdf")}
    
    # Get all output JSON files
    output_keys = list_s3_keys(s3_client, output_bucket, output_prefix)
    output_jsons = {k for k in output_keys if k.endswith(".json")}
    
    # Create mapping of base names to actual files
    input_base_names = {get_base_name(k): k for k in input_pdfs}
    output_base_names = {get_base_name(k): k for k in output_jsons}
    
    # Find missing and extra files
    missing = set(input_base_names.keys()) - set(output_base_names.keys())
    unprocessed = set(output_base_names.keys()) - set(input_base_names.keys())
    processed = set(input_base_names.keys()) & set(output_base_names.keys())
    
    # Print report
    print(f"\n{Style.BRIGHT}{Fore.CYAN}Prefix: {input_prefix}{Style.RESET_ALL}")
    print(f"  Input files: {Fore.YELLOW}{len(input_pdfs)}{Style.RESET_ALL}")
    print(f"  Output files: {Fore.YELLOW}{len(output_jsons)}{Style.RESET_ALL}")
    print(f"  Processed: {Fore.GREEN}{len(processed)}{Style.RESET_ALL}")
    
    if processed:
        print(f"\n  {Fore.GREEN}✓ Successfully processed files:{Style.RESET_ALL}")
        for base_name in sorted(processed):
            input_file = input_base_names[base_name]
            output_file = output_base_names[base_name]
            output_method = "pypdf" if "_pypdf.json" in output_file else "textract"
            print(f"    {Fore.GREEN}✓ {os.path.basename(input_file)} → {os.path.basename(output_file)} [{output_method}]{Style.RESET_ALL}")
    
    if missing:
        print(f"\n  {Fore.RED}✗ Files not yet processed:{Style.RESET_ALL}")
        for base_name in sorted(missing):
            input_file = input_base_names[base_name]
            print(f"    {Fore.RED}✗ {os.path.basename(input_file)}{Style.RESET_ALL}")
    
    if unprocessed:
        print(f"\n  {Fore.YELLOW}⚠ Output files without matching input:{Style.RESET_ALL}")
        for base_name in sorted(unprocessed):
            output_file = output_base_names[base_name]
            print(f"    {Fore.YELLOW}⚠ {os.path.basename(output_file)}{Style.RESET_ALL}")
    
    return len(missing) == 0


def main() -> int:
    # Initialize colorama for cross-platform color support
    init(autoreset=True)
    
    # Hardcoded configuration values
    INPUT_BUCKET = "cv-input-bucket-poc"
    OUTPUT_BUCKET = "cv-output-bucket-poc"
    VALID_PREFIX = "cvs/valid"
    INVALID_PREFIX = "cvs/invalid"

    print(f"{Style.BRIGHT}{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    print(f"{Style.BRIGHT}{Fore.CYAN}  CV Processing Completeness Check{Style.RESET_ALL}")
    print(f"{Style.BRIGHT}{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    print(f"\nInput Bucket:  {Fore.CYAN}{INPUT_BUCKET}{Style.RESET_ALL}")
    print(f"Output Bucket: {Fore.CYAN}{OUTPUT_BUCKET}{Style.RESET_ALL}")

    s3 = boto3.client("s3")

    # Check valid CVs
    valid_ok = check_processing_completeness(
        s3,
        INPUT_BUCKET,
        OUTPUT_BUCKET,
        VALID_PREFIX,
        VALID_PREFIX
    )
    
    # Check invalid CVs
    invalid_ok = check_processing_completeness(
        s3,
        INPUT_BUCKET,
        OUTPUT_BUCKET,
        INVALID_PREFIX,
        INVALID_PREFIX
    )

    print(f"\n{Style.BRIGHT}{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    if valid_ok and invalid_ok:
        print(f"{Style.BRIGHT}{Fore.GREEN}✓ All uploaded files have been processed!{Style.RESET_ALL}")
        return 0
    else:
        print(f"{Style.BRIGHT}{Fore.RED}✗ Some files are missing or not yet processed!{Style.RESET_ALL}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
