import json
import PyPDF2
import os
import re
import time
from google import genai
from google.genai import types
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))


MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 1


def make_gemini_request_with_retry(model_name, contents, config):
    """
    Makes a request to the Gemini API with retry logic for 503 errors.
    """
    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config
            )
            return response  # Success
        except Exception as e:  # Ideally, catch specific _exceptions.ServiceUnavailable
            # Check if the error message contains '503' or 'UNAVAILABLE' or 'overloaded'
            # This is a basic check; more specific exception catching is better if available.
            error_str = str(e).lower()
            is_overload_error = "503" in error_str or "unavailable" in error_str or "overloaded" in error_str

            if is_overload_error and attempt < MAX_RETRIES - 1:
                wait_time = INITIAL_BACKOFF_SECONDS * (2 ** attempt)
                # jitter = random.uniform(0, wait_time * 0.1)  # Add jitter
                actual_wait_time = wait_time + jitter
                print(
                    f"API overloaded (attempt {attempt + 1}/{MAX_RETRIES}). Retrying in {actual_wait_time:.2f} seconds...")
                time.sleep(actual_wait_time)
            else:
                # If not a 503-like error or it's the last attempt, re-raise
                raise e
    # Should not be reached if MAX_RETRIES > 0, as the loop will either return or raise
    raise Exception("API request failed after all retries.")


def extract_json_from_pdf(pdf_path):
    """
    Extract text content from a PDF file and convert to JSON structure

    Parameters:
        pdf_path (str): Path to the PDF file

    Returns:
        dict: Extracted resume data in JSON format
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    uploaded_file = client.files.upload(
        file=pdf_path, config=dict(mime_type='application/pdf'))

    prompt = f"""Extract the text from the PDF given as is.
                # In the Experience section make sure to extract the location of the company, the title of the job properly without the tools used and the tools used in that company.
                # Sometimes the tools are mentioned in the title section separated by a dash. Only if these tools are not mentioned then add 3 tools according to the work experience.
                Convert this into a sensible structured json response. The output should be strictly be json with no extra commentary
                # In the Technical Knowledge section make sure to extract the tools as a dictionary of list.
                Once the json is generated, make sure to check the json for any errors and also see that it is according to the prompt and fix them.
                
                Ensure that all property names and string values are enclosed in DOUBLE QUOTES, not single quotes.
                Format the output as a valid JSON object according to RFC 8259 specification."""

    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash-latest",
            contents=[uploaded_file, prompt],
            config=types.GenerateContentConfig(
                temperature=0.0,
                top_p=0.5,
                top_k=40,
                max_output_tokens=2048,
                response_mime_type="application/json"
            )
        )

        # Extract and parse JSON response
        try:
            # Try to parse the result directly
            resume_json = json.loads(response.text)
            print("Successfully parsed PDF extraction JSON")

            # Save the extracted JSON
            with open("resume.json", 'w', encoding='utf-8') as json_file:
                json.dump(resume_json, json_file, ensure_ascii=False, indent=4)

            return resume_json

        except json.JSONDecodeError as e:
            print(f"JSON parse error when extracting from PDF: {str(e)}")

            # If direct parsing fails, try to extract JSON from text
            text = response.text
            # Find JSON content between curly braces
            start_idx = text.find('{')
            end_idx = text.rfind('}') + 1

            if start_idx >= 0 and end_idx > start_idx:
                json_str = text[start_idx:end_idx]

                try:
                    # Try to clean the JSON before parsing
                    cleaned_json = json_str
                    # Replace single quotes with double quotes for property names and strings
                    cleaned_json = re.sub(
                        r"(?<={|,)\s*'([^']+)'(?=\s*:)", r'"\1"', cleaned_json)
                    cleaned_json = re.sub(
                        r":\s*'([^']*)'(?=\s*[,}])", r':"\1"', cleaned_json)

                    # Remove any code block markers
                    cleaned_json = re.sub(r'```json|```', '', cleaned_json)

                    resume_json = json.loads(cleaned_json)
                    print("Successfully extracted and cleaned JSON from PDF extraction")

                    # Save the extracted JSON
                    with open("resume.json", 'w', encoding='utf-8') as json_file:
                        json.dump(resume_json, json_file,
                                  ensure_ascii=False, indent=4)

                    return resume_json

                except json.JSONDecodeError as e2:
                    print(f"Secondary JSON parse error: {str(e2)}")

                    # Try one more approach - ask Gemini to fix the JSON
                    try:
                        fix_prompt = f"""
                        This JSON from PDF extraction has syntax errors. Please fix it to be valid JSON with double quotes for all property names and string values:
                        
                        {json_str}
                        
                        Return ONLY the fixed JSON.
                        """

                        fix_response = client.models.generate_content(
                            model="gemini-2.0-flash",
                            contents=fix_prompt,
                            config=types.GenerateContentConfig(
                                temperature=0,
                                response_mime_type="application/json"
                            )
                        )

                        # Try to parse the fixed JSON
                        fixed_json = fix_response.text.strip()
                        if fixed_json.startswith("```") and fixed_json.endswith("```"):
                            fixed_json = fixed_json[fixed_json.find(
                                "{"):fixed_json.rfind("}")+1]

                        resume_json = json.loads(fixed_json)
                        print(
                            "Successfully fixed PDF extraction JSON with secondary Gemini call")

                        # Save the extracted JSON
                        with open("resume.json", 'w', encoding='utf-8') as json_file:
                            json.dump(resume_json, json_file,
                                      ensure_ascii=False, indent=4)

                        return resume_json

                    except Exception as e3:
                        print(f"Failed to fix PDF extraction JSON: {str(e3)}")
                        raise ValueError(
                            f"Failed to parse PDF extraction JSON after multiple attempts: {str(e2)}")
            else:
                raise ValueError(
                    "Could not extract valid JSON from PDF extraction - no JSON structure found")

    except Exception as e:
        print(f"Error extracting JSON from PDF: {str(e)}")

        # Create fallback minimal JSON structure
        fallback_json = {
            "contact_info": {
                "name": "Resume Owner",
                "email": "",
                "phone": "",
                "location": ""
            },
            "summary": "Professional with experience and skills.",
            "skills": {"technical_skills": []},
            "experience": [],
            "education": []
        }

        print("Created minimal fallback JSON structure")
        return fallback_json


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


if __name__ == "__main__":
    # read_job_description("job_description.txt")
    extract_json_from_pdf("Rahul_Resume.pdf")
