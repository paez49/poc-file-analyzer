# POC File Analyzer

An AWS-based proof-of-concept system for automated CV/resume processing using serverless architecture. This system extracts text from PDF resumes using PyPDF and AWS Textract (as fallback), then structures the information using AWS Bedrock AI for intelligent parsing.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Project Phases](#project-phases)
- [Quick Start Guide](#quick-start-guide)
- [Detailed Setup](#detailed-setup)
- [Verification and Monitoring](#verification-and-monitoring)
- [Configuration](#configuration)

## Architecture Overview

The system consists of the following AWS components:

- **S3 Buckets**: 
  - `cv-input-bucket-poc` - Stores uploaded CV PDFs
  - `cv-output-bucket-poc` - Stores extracted and structured JSON data
- **SQS Queue**: Decouples S3 events from Lambda processing
- **Lambda Function**: Processes PDFs and extracts structured information
- **AWS Textract**: OCR service for scanned or image-based PDFs
- **AWS Bedrock**: AI service (Nova Micro) for intelligent data extraction

**Processing Flow**:
1. PDF uploaded to input S3 bucket
2. S3 triggers notification to SQS queue
3. Lambda function processes the message
4. Text extracted using PyPDF (or Textract if PyPDF fails)
5. Bedrock structures the text into JSON format
6. Structured JSON saved to output S3 bucket

## Project Phases

### Phase 1: Infrastructure Setup

Deploy the AWS infrastructure using CDK (Cloud Development Kit).

**Components deployed**:
- Two S3 buckets (input and output)
- SQS queue for event processing
- Lambda function with PyPDF layer
- IAM roles and permissions
- S3 event notifications

**Key files**:
- `poc-infrastructure/poc_infrastructure/poc_infrastructure_stack.py` - CDK stack definition
- `poc-infrastructure/app.py` - CDK app entry point
- `poc-infrastructure/lambda/file-processor/lambda.py` - Lambda handler code

### Phase 2: Data Generation and Upload

Generate test CV data and upload to S3 for processing.

**Features**:
- Generates 1000 test CVs (900 valid, 100 invalid)
- Valid CVs contain structured text (name, email, experience, education, skills)
- Invalid CVs use scanned/image-based PDFs requiring OCR
- Random upload order to simulate real-world scenarios
- Visual progress tracking with colored output

**Key files**:
- `upload_cvs.py` - CV generation and upload script
- `generated_cvs/` - Directory containing generated valid CVs
- `invalid_cvs/` - Directory containing invalid/scanned CVs

### Phase 3: Automated Processing

Lambda function automatically processes uploaded CVs.

**Processing steps**:
1. Downloads PDF from S3
2. Attempts text extraction using PyPDF (local, fast)
3. Falls back to AWS Textract if PyPDF fails (OCR)
4. Sends extracted text to AWS Bedrock
5. Bedrock extracts structured fields: name, email, work experience, education, skills
6. Saves JSON output with appropriate suffix (`_pypdf.json` or `_textract.json`)

**Key files**:
- `poc-infrastructure/lambda/file-processor/lambda.py` - Processing logic

### Phase 4: Verification and Monitoring

Verify all files have been processed successfully.

**Features**:
- Compares input PDFs with output JSON files
- Tracks processing status (processed, missing, extra files)
- Distinguishes between PyPDF and Textract extraction methods
- Colored console output for easy reading
- Separate tracking for valid and invalid CV prefixes

**Key files**:
- `check_file_completeness.py` - Verification script

## Quick Start Guide

### Prerequisites

- Python 3.11+
- AWS CLI configured with appropriate credentials
- AWS CDK CLI installed (`npm install -g aws-cdk`)
- Node.js (for CDK)

### Step 1: Clone and Setup Environment

```bash
# Clone the repository
git clone https://github.com/paez49/poc-file-analyzer
cd poc-file-analyzer

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Deploy Infrastructure

```bash
# Navigate to infrastructure directory
cd poc-infrastructure

# Install CDK dependencies
pip install -r requirements.txt

# Bootstrap CDK (first time only)
cdk bootstrap

# Deploy the stack
cdk deploy
```

**Note**: Review the changes and confirm deployment when prompted.

### Step 3: Generate and Upload Test Data

```bash
# Return to project root
cd ..

# Ensure you have an invalid CV sample
# Place a scanned/image-based PDF in: invalid_cvs/NoDigitalCV.pdf

# Run upload script
python upload_cvs.py
```

This will:
- Generate 900 valid CV PDFs
- Upload all files (900 valid + 100 invalid) in random order
- Show upload progress with colored output

### Step 4: Monitor Processing

The Lambda function will automatically process files as they're uploaded. Monitor progress:

```bash
# Check AWS CloudWatch Logs
aws logs tail /aws/lambda/PocCvBedrockStack-CVProcessorLambda --follow

# Or check S3 output bucket
aws s3 ls s3://cv-output-bucket-poc/cvs/valid/ --recursive
aws s3 ls s3://cv-output-bucket-poc/cvs/invalid/ --recursive
```

### Step 5: Verify Completeness

```bash
# Run verification script
python check_file_completeness.py
```

This will show:
- Total input and output files
- Successfully processed files
- Missing or unprocessed files
- Processing method used (PyPDF vs Textract)

## Detailed Setup

### Infrastructure Details

The CDK stack creates:

```
├── cv-input-bucket-poc/
│   ├── cvs/valid/          # Valid CV PDFs
│   └── cvs/invalid/        # Scanned/image CVs
├── cv-output-bucket-poc/
│   ├── cvs/valid/          # Extracted JSON (valid)
│   └── cvs/invalid/        # Extracted JSON (invalid)
├── CVProcessingQueue       # SQS queue
└── CVProcessorLambda       # Lambda function
```

**Lambda Configuration**:
- Runtime: Python 3.11
- Memory: 1024 MB
- Timeout: 180 seconds
- Layer: PyPDF library
- Environment: `OUTPUT_BUCKET=cv-output-bucket-poc`

### Python Dependencies

**Root level** (`requirements.txt`):
```
boto3==1.40.69
colorama==0.4.6
fpdf==1.7.2
tqdm==4.67.1
```

**Lambda layer** (`poc-infrastructure/lambda/file-processor/requirements.txt`):
```
pypdf==6.1.1
```

## Verification and Monitoring

### Check Processing Status

```bash
python check_file_completeness.py
```

**Output interpretation**:
- ✓ Green: Successfully processed
- ✗ Red: Not yet processed or missing
- ⚠ Yellow: Output without matching input

### Manual S3 Inspection

```bash
# List all input files
aws s3 ls s3://cv-input-bucket-poc/cvs/ --recursive

# List all output files
aws s3 ls s3://cv-output-bucket-poc/cvs/ --recursive

# Download a sample output
aws s3 cp s3://cv-output-bucket-poc/cvs/valid/cv_1_pypdf.json ./
cat cv_1_pypdf.json
```

### CloudWatch Logs

```bash
# View recent logs
aws logs tail /aws/lambda/PocCvBedrockStack-CVProcessorLambda --since 1h

# Follow logs in real-time
aws logs tail /aws/lambda/PocCvBedrockStack-CVProcessorLambda --follow
```

## Configuration

### Bucket Names

Edit in `poc-infrastructure/poc_infrastructure/poc_infrastructure_stack.py`:

```python
input_bucket = s3.Bucket(
    self, "InputCVBucket",
    bucket_name="cv-input-bucket-poc",  # Change here
    ...
)
```

### Test Data Volume

Edit in `upload_cvs.py`:

```python
TOTAL_FILES = 1000      # Total files to generate
INVALID_COUNT = 100     # Number of invalid/scanned CVs
VALID_COUNT = TOTAL_FILES - INVALID_COUNT  # 900 valid CVs
```

### Lambda Timeout and Memory

Edit in `poc-infrastructure/poc_infrastructure/poc_infrastructure_stack.py`:

```python
processor_fn = _lambda.Function(
    self, "CVProcessorLambda",
    timeout=Duration.seconds(180),  # Adjust timeout
    memory_size=1024,               # Adjust memory
    ...
)
```

### Bedrock Model

Edit in `poc-infrastructure/lambda/file-processor/lambda.py`:

```python
response = bedrock.invoke_model(
    modelId="us.amazon.nova-micro-v1:0",  # Change model here
    ...
)
```

## Cleanup

To avoid AWS charges, delete all resources:

```bash
# Delete CDK stack
cd poc-infrastructure
cdk destroy

# Verify S3 buckets are deleted
aws s3 ls | grep cv-bucket-poc
```

## Troubleshooting

### Lambda Timeout Errors
- Increase timeout in CDK stack (default: 180s)
- Increase memory allocation (default: 1024 MB)

### Text Extraction Fails
- Verify PDF is not corrupted
- Check CloudWatch logs for specific errors
- Ensure Textract permissions are granted

### Bedrock Errors
- Verify Bedrock model access in your AWS region
- Check IAM permissions for `bedrock:InvokeModel`
- Ensure region supports Nova Micro model

### Processing Completeness Issues
- Wait for Lambda to finish processing (can take time for 1000 files)
- Check SQS queue for stuck messages
- Review CloudWatch logs for Lambda errors

## License

This is a proof-of-concept project for demonstration purposes.

## Contributing

This is a POC project. For production use, consider:
- Adding error handling and retry logic
- Implementing DLQ (Dead Letter Queue)
- Adding monitoring and alerting
- Implementing cost optimization strategies
- Adding validation and sanitization
- Implementing proper logging and tracing