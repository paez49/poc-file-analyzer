import boto3
import random
import os
from fpdf import FPDF
from tqdm import tqdm
from colorama import Fore, init

# Initialize colorama
init(autoreset=True)


s3 = boto3.client("s3")
bucket_name = "cv-input-bucket-poc"

INPUT_DIR = "generated_cvs"  
INPUT_INVALID_DIR = "invalid_cvs"    
TOTAL_FILES = 1000
INVALID_COUNT = 100
VALID_COUNT = TOTAL_FILES - INVALID_COUNT

os.makedirs(INPUT_DIR, exist_ok=True)

def create_valid_pdf(file_path, idx):
    """Creates a valid PDF with readable text"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Curriculum Vitae - Candidato {idx}", ln=True)
    pdf.multi_cell(0, 10, txt=(
        f"Nombre: Candidato {idx}\n"
        f"Correo: candidato{idx}@correo.com\n"
        f"Experiencia: {random.randint(1, 10)} años en desarrollo de software.\n"
        f"Educación: Ingeniería de Sistemas.\n"
        f"Habilidades: Python, AWS, Docker, Machine Learning."
    ))
    pdf.output(file_path)


def upload_file(file_path, s3_key):
    """Uploads a local file to S3 bucket"""
    try:
        s3.upload_file(file_path, bucket_name, s3_key)
    except Exception as e:
        print(f"{Fore.RED}Error uploading {file_path}: {e}")


print(f"{Fore.CYAN}Generating {VALID_COUNT} valid PDFs...")
for i in tqdm(range(1, VALID_COUNT + 1)):
    file_path = os.path.join(INPUT_DIR, f"cv_{i}.pdf")
    create_valid_pdf(file_path, i)

print(f"{Fore.GREEN}✓ Valid PDFs generated successfully.")

# Prepare list of all files to upload (valid and invalid)
files_to_upload = []

# Add valid files to the list
for i in range(1, VALID_COUNT + 1):
    file_path = os.path.join(INPUT_DIR, f"cv_{i}.pdf")
    key = f"cvs/valid/cv_{i}.pdf"
    files_to_upload.append((file_path, key, "valid"))

# Add invalid files to the list
if INVALID_COUNT > 0:
    source_cv = os.path.join(INPUT_INVALID_DIR, "NoDigitalCV.pdf")
    for i in range(1, INVALID_COUNT + 1):
        key = f"cvs/invalid/cv_invalid_{i}.pdf"
        files_to_upload.append((source_cv, key, "invalid"))

# Randomly shuffle the upload order
random.shuffle(files_to_upload)

print(f"{Fore.CYAN}Uploading {TOTAL_FILES} files to S3 in random order...")
print(f"{Fore.YELLOW}Upload sequence:")

# Display the upload sequence
for idx, (file_path, key, file_type) in enumerate(files_to_upload, 1):
    file_name = os.path.basename(key)
    color = Fore.CYAN if file_type == "valid" else Fore.YELLOW
    print(f"  {idx}. {color}[{file_type.upper()}] {file_name}")

print()  # Add blank line before progress bar

# Upload files in random order
for file_path, key, file_type in tqdm(files_to_upload, desc="Uploading"):
    upload_file(file_path, key)

print(f"{Fore.GREEN}✓ All files were successfully uploaded to S3 in random order.")
