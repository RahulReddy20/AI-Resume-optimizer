import json
import PyPDF2
import os
from google import genai
from google.genai import types
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))


def extract_json_from_pdf(pdf_path):
    """
    Extract text content from a PDF file

    Parameters:
        pdf_path (str): Path to the PDF file

    Returns:
        str: Extracted text content
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    uploaded_file = client.files.upload(
        file=pdf_path, config=dict(mime_type='application/pdf'))

    prompt = f"""Extract the text from the PDF given as is.
                In the Expereince section make sure to extract the location of the company, the title of the job properly without the tools used and the tools used in that company.
                Sometimes the tools are mentioned in the title section separated by a dash.
                Only if the tools are not mentioned then add 3-4 tools according to the work experience.
                Convert this into a sensible structured json response. The output should be strictly be json with no extra commentary
                In the Technical Knowledge section make sure to extract the tools as a dictionary of list.
                Once the json is generated, make sure to check the json for any errors and also see that it is according to the prompt and fix them."""

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[uploaded_file, prompt],
        config=types.GenerateContentConfig(
            temperature=0.0,
            top_p=0.5,
            top_k=40,
            max_output_tokens=2048,
            response_mime_type="application/json"
        )
    )
    resume_json = json.loads(response.text)
    # print(resume_json)
    with open("resume.json", 'w', encoding='utf-8') as json_file:
        json.dump(resume_json, json_file, ensure_ascii=False, indent=4)

    return resume_json


def extract_text_from_pdf(pdf_path):
    """
    Extract text content from a PDF file

    Parameters:
        pdf_path (str): Path to the PDF file

    Returns:
        str: Extracted text content
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    text_content = ""

    try:
        # Open the PDF file in binary read mode
        with open(pdf_path, 'rb') as pdf_file:
            # Create PDF reader object
            pdf_reader = PyPDF2.PdfReader(pdf_file)

            # Get number of pages
            num_pages = len(pdf_reader.pages)

            # Extract text from each page
            for page_num in range(num_pages):
                page = pdf_reader.pages[page_num]
                text_content += page.extract_text() + "\n"

    except Exception as e:
        raise Exception(f"Error extracting text from PDF: {str(e)}")

    return text_content


def read_job_description(job_input):
    """
    Read job description from either a text file or a string

    Parameters:
        job_input (str): Either a file path or the job description text

    Returns:
        str: Job description text
    """
    # Check if input is a file path
    if os.path.exists(job_input) and job_input.lower().endswith(('.txt', '.docx', '.pdf')):
        if job_input.lower().endswith('.pdf'):
            return extract_text_from_pdf(job_input)
        elif job_input.lower().endswith('.docx'):
            # For future implementation: extract text from Word file
            raise NotImplementedError(
                "DOCX parsing not implemented for job descriptions")
        else:  # .txt
            with open(job_input, 'r', encoding='utf-8') as file:
                return file.read()
    else:
        # Assume the input is the job description text itself
        return job_input


# if __name__ == "__main__":
#     # read_job_description("job_description.txt")
#     extract_text_from_pdf("Rahul_Resume.pdf")
