import boto3
import os
import json
import time
from pypdf import PdfReader
from botocore.exceptions import ClientError

s3 = boto3.client("s3")
textract = boto3.client("textract")
bedrock = boto3.client("bedrock-runtime")
output_bucket = os.environ["OUTPUT_BUCKET"]


def extract_text_raw_local(pdf_path):
    """Extracts RAW text locally using PyPDF2"""
    try:
        reader = PdfReader(pdf_path)
        text = "\n".join([page.extract_text() or "" for page in reader.pages])
        return text.strip()
    except Exception as e:
        print(f"⚠️ Error extracting text locally: {e}")
        return ""


def extract_text_with_textract(bucket, key):
    """Uses Amazon Textract for OCR and returns RAW text"""
    try:
        response = textract.start_document_text_detection(
            DocumentLocation={"S3Object": {"Bucket": bucket, "Name": key}}
        )
        job_id = response["JobId"]
        print(f"⌛ Waiting for Textract (JobId={job_id})...")

        while True:
            job_status = textract.get_document_text_detection(JobId=job_id)
            status = job_status["JobStatus"]
            if status in ["SUCCEEDED", "FAILED"]:
                break
            time.sleep(2)

        if status == "SUCCEEDED":
            raw_text = ""
            for block in job_status["Blocks"]:
                if block["BlockType"] == "LINE":
                    raw_text += block["Text"] + "\n"
            print("✅ Textract completed successfully.")
            print(f"Textract text preview: {raw_text.strip()[:150]}...")
            return raw_text.strip()
        else:
            print("❌ Textract failed.")
            return ""
    except ClientError as e:
        print(f"Error in Textract: {e}")
        return ""


def extract_json_with_bedrock(raw_text):
    """Sends RAW text to Bedrock and returns structured JSON"""
    prompt = f"""
    Below is the text from a resume (CV):

    {raw_text[:4000]}

    Extract and return in JSON format the following fields:
    - name
    - email
    - work experience
    - education
    - technical skills

    Respond only with valid JSON.
    """
    try:
        response = bedrock.invoke_model(
            modelId="us.amazon.nova-micro-v1:0",
            body=json.dumps(
                {
                    "messages": [{"role": "user", "content": [{"text": prompt}]}]
                }
            ),
            contentType="application/json",
            accept="application/json",
        )
        response_body = json.loads(response["body"].read())
        # Extract the text from Nova's response format
        result_text = response_body["output"]["message"]["content"][0]["text"]
        return json.loads(result_text)
    except Exception as e:
        print(f"Error in Bedrock: {e}")
        return {"error": "Could not process with Bedrock"}


def handler(event, context):
    for record in event["Records"]:
        message = json.loads(record["body"])
        s3_info = message["Records"][0]["s3"]
        bucket = s3_info["bucket"]["name"]
        key = s3_info["object"]["key"]

        tmp_path = f"/tmp/{os.path.basename(key)}"
        s3.download_file(bucket, key, tmp_path)

        print(f"📥 Processing file {key}...")

        raw_text = extract_text_raw_local(tmp_path)
        extraction_method = "pypdf"  # Default to pypdf

        if not raw_text:
            print("⚠️ Local extraction failed. Switching to Textract...")
            raw_text = extract_text_with_textract(bucket, key)
            extraction_method = "textract"  # Changed to textract

        if not raw_text:
            print("❌ Could not extract text from CV.")
            continue

        structured_json = extract_json_with_bedrock(raw_text)

        # Add extraction method suffix to output filename
        output_key = key.replace(".pdf", f"_{extraction_method}.json")
        s3.put_object(
            Bucket=output_bucket,
            Key=output_key,
            Body=json.dumps(structured_json, indent=2).encode("utf-8"),
        )

        print(f"✅ JSON saved to {output_bucket}/{output_key}")

    return {"status": "ok"}
