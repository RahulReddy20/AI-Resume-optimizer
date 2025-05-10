import PyPDF2
import os


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
