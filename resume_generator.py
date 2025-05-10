import os
import json
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from google import genai
from dotenv import load_dotenv
from google.genai import types
import re

# Load environment variables
load_dotenv()

# Configure the Gemini API client
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))


def generate_optimized_resume(resume_text, job_description, missing_skills, similarity_score):
    """
    Generate an optimized resume based on the job description using Gemini API

    Parameters:
        resume_text (str): Original resume text
        job_description (str): Job description text
        missing_skills (list): List of skills in the job description but not in the resume
        similarity_score (float): Similarity score between resume and job description

    Returns:
        dict: JSON structure of the optimized resume
    """
    # Prepare prompt for Gemini
    prompt = f"""
    You are a professional resume writer tasked with optimizing a resume to better match a job description.
    
    ORIGINAL RESUME:
    {resume_text}
    
    JOB DESCRIPTION:
    {job_description}
    
    ANALYSIS:
    - Current match score: {similarity_score:.2f} out of 1.00
    - Missing skills/keywords: {', '.join(missing_skills) if isinstance(missing_skills, list) else str(missing_skills)}
    
    Please rewrite the resume to better match the job description while maintaining truthfulness.
    Focus on highlighting relevant experience, rewording skills, and restructuring content to showcase
    the candidate's fit for this specific position.
    
    YOUR OUTPUT MUST INCLUDE: 
    - A "summary" or "objective" field
    - Complete contact information
    - Education details
    - Skills formatted properly
    - Experience entries with descriptions
    
    Format the output as a JSON object with the following structure:
    {{
        "contact_info": {{
            "name": "...",
            "email": "...",
            "phone": "...",
            "location": "...",
            "linkedin": "..." (if available)
        }},
        "summary": "A concise professional summary or objective statement",
        "skills": {{
            "technical_skills": ["skill1", "skill2", ...],
            "soft_skills": ["skill1", "skill2", ...] (if available),
            "other_skills": ["skill1", "skill2", ...] (if available)
        }},
        "experience": [
            {{
                "title": "...",
                "company": "...",
                "location": "...",
                "dates": "...",
                "description": ["bullet point 1", "bullet point 2", ...]
            }},
            ...
        ],
        "education": [
            {{
                "degree": "...",
                "institution": "...",
                "dates": "...",
                "details": "..." (optional)
            }},
            ...
        ],
        "projects": [
            {{
                "title": "...",
                "description": "..."
            }},
            ...
        ] (if available),
        "certifications": [
            {{
                "name": "...",
                "issuer": "...",
                "date": "..."
            }},
            ...
        ] (if available),
        "activities": ["activity1", "activity2", ...] (if available),
        "leadership": ["leadership1", "leadership2", ...] (if available)
    }}
    
    Only include sections that are present in the original resume. Keep the content TRUTHFUL and based on the original resume.
    Output ONLY the JSON with no other text before or after. Double-check that your JSON includes all required fields, especially the "summary" field.
    """

    try:
        # Generate content with Gemini
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                top_p=0.95,
                top_k=40,
                max_output_tokens=2048,
                response_mime_type="application/json"
            )
        )

        # Extract and parse JSON response
        try:
            # Try to parse the result directly
            resume_json = json.loads(response.text)
            # Validate the response has the expected structure
            if not isinstance(resume_json, dict):
                raise ValueError("Response is not a valid JSON object")

            # Check and fix missing required sections
            if "contact_info" not in resume_json:
                resume_json["contact_info"] = {
                    "name": "", "email": "", "phone": "", "location": ""}

            if "summary" not in resume_json:
                resume_json["summary"] = "Professional seeking opportunities in the field."

            # Convert any dict_keys objects (which are not JSON serializable) to lists
            if "skills" in resume_json and isinstance(resume_json["skills"], dict):
                for key in list(resume_json["skills"].keys()):
                    skills_value = resume_json["skills"][key]
                    if not isinstance(skills_value, list):
                        if hasattr(skills_value, 'keys'):  # Handle dict_keys objects
                            resume_json["skills"][key] = list(skills_value)
                        else:
                            # Convert other non-list types to a list with a single element
                            resume_json["skills"][key] = [str(skills_value)]

            print("Resume JSON successfully generated and validated")

        except json.JSONDecodeError as e:
            print(f"JSON parse error: {str(e)}")
            # If direct parsing fails, try to extract JSON from text
            text = response.text
            # Find JSON content between curly braces
            start_idx = text.find('{')
            end_idx = text.rfind('}') + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = text[start_idx:end_idx]
                try:
                    resume_json = json.loads(json_str)
                    print("Successfully extracted JSON from response text")
                except json.JSONDecodeError as e2:
                    print(f"Secondary JSON parse error: {str(e2)}")
                    # Last resort: Try to clean up JSON with regex
                    import re
                    # Remove non-JSON content that might be causing issues
                    json_str = re.sub(r'```json|```', '', json_str)
                    # Try again with cleaned text
                    try:
                        resume_json = json.loads(json_str)
                        print("Successfully parsed JSON after cleanup")
                    except:
                        raise ValueError(
                            f"Failed to parse JSON after multiple attempts: {str(e2)}")
            else:
                raise ValueError(
                    "Could not extract valid JSON from response - no JSON structure found")

        return resume_json

    except Exception as e:
        print(f"Error generating optimized resume: {str(e)}")

        # Create fallback minimal JSON with original resume data if possible
        try:
            # Extract basic info for a minimal resume
            fallback_resume = {
                "contact_info": {
                    "name": "Resume Owner",
                    "email": "",
                    "phone": "",
                    "location": ""
                },
                "summary": "Professional with relevant experience and skills.",
                "skills": {"technical_skills": []},
                "experience": [],
                "education": []
            }

            print("Created minimal fallback resume structure")
            return fallback_resume
        except:
            print("Could not create fallback resume")
            return None


def create_resume_docx(resume_json, output_path="optimized_resume.docx"):
    """
    Create a formatted Word document from resume JSON

    Parameters:
        resume_json (dict): Resume data in JSON format
        output_path (str): Output path for the Word document

    Returns:
        bool: Success status
    """
    try:
        # Create a new Document
        doc = Document()

        # Contact Information
        name = doc.add_paragraph()
        name_run = name.add_run(resume_json["contact_info"]["name"])
        name_run.bold = True
        name_run.font.size = Pt(16)
        name.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

        contact = doc.add_paragraph()
        contact_info = [
            resume_json["contact_info"].get("email", ""),
            resume_json["contact_info"].get("phone", ""),
            resume_json["contact_info"].get("location", "")
        ]
        if "linkedin" in resume_json["contact_info"]:
            contact_info.append(resume_json["contact_info"]["linkedin"])
        contact.add_run(" | ".join(filter(None, contact_info)))
        contact.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

        # Summary
        doc.add_paragraph()
        summary_heading = doc.add_paragraph()
        summary_heading.add_run("SUMMARY").bold = True
        doc.add_paragraph(resume_json["summary"])

        # Skills
        doc.add_paragraph()
        skills_heading = doc.add_paragraph()
        skills_heading.add_run("SKILLS").bold = True
        skills_para = doc.add_paragraph()
        all_skills = []
        if isinstance(resume_json["skills"], list):
            all_skills = resume_json["skills"]
        elif isinstance(resume_json["skills"], dict):
            if "technical_skills" in resume_json["skills"]:
                all_skills.extend(resume_json["skills"]["technical_skills"])
            if "soft_skills" in resume_json["skills"]:
                all_skills.extend(resume_json["skills"]["soft_skills"])
            if "other_skills" in resume_json["skills"]:
                all_skills.extend(resume_json["skills"]["other_skills"])
        skills_para.add_run(", ".join(all_skills))

        # Experience
        doc.add_paragraph()
        exp_heading = doc.add_paragraph()
        exp_heading.add_run("EXPERIENCE").bold = True

        for job in resume_json["experience"]:
            job_title = doc.add_paragraph()
            title_company = f"{job['title']} - {job['company']}"
            job_title.add_run(title_company).bold = True
            dates = doc.add_paragraph()
            dates.add_run(job["dates"]).italic = True

            for bullet in job["description"]:
                bullet_point = doc.add_paragraph()
                bullet_point.style = 'List Bullet'
                bullet_point.add_run(bullet)

        # Education
        doc.add_paragraph()
        edu_heading = doc.add_paragraph()
        edu_heading.add_run("EDUCATION").bold = True

        for edu in resume_json["education"]:
            edu_degree = doc.add_paragraph()
            edu_degree.add_run(
                f"{edu['degree']} - {edu['institution']}").bold = True
            dates = doc.add_paragraph()
            dates.add_run(edu["dates"]).italic = True
            if "details" in edu and edu["details"]:
                details = doc.add_paragraph()
                details.add_run(edu["details"])

        # Projects (if available)
        if "projects" in resume_json and resume_json["projects"]:
            doc.add_paragraph()
            proj_heading = doc.add_paragraph()
            proj_heading.add_run("PROJECTS").bold = True

            for project in resume_json["projects"]:
                proj_name = doc.add_paragraph()
                proj_name.add_run(project["title"]).bold = True
                desc = doc.add_paragraph()
                desc.add_run(project["description"])

        # Certifications (if available)
        if "certifications" in resume_json and resume_json["certifications"]:
            doc.add_paragraph()
            cert_heading = doc.add_paragraph()
            cert_heading.add_run("CERTIFICATIONS").bold = True

            for cert in resume_json["certifications"]:
                cert_name = doc.add_paragraph()
                cert_name.add_run(
                    f"{cert['name']} - {cert['issuer']}").bold = True
                date = doc.add_paragraph()
                date.add_run(cert["date"]).italic = True

        # Activities (if available)
        if "activities" in resume_json and resume_json["activities"]:
            doc.add_paragraph()
            act_heading = doc.add_paragraph()
            act_heading.add_run("EXTRA-CURRICULAR ACTIVITIES").bold = True

            for activity in resume_json["activities"]:
                act_bullet = doc.add_paragraph()
                act_bullet.style = 'List Bullet'
                act_bullet.add_run(activity)

        # Leadership (if available)
        if "leadership" in resume_json and resume_json["leadership"]:
            doc.add_paragraph()
            lead_heading = doc.add_paragraph()
            lead_heading.add_run("LEADERSHIP").bold = True

            for lead_item in resume_json["leadership"]:
                lead_bullet = doc.add_paragraph()
                lead_bullet.style = 'List Bullet'
                lead_bullet.add_run(lead_item)

        # Save the document
        doc.save(output_path)
        return True

    except Exception as e:
        print(f"Error creating resume document: {str(e)}")
        return False


def create_resume_latex(resume_json, output_path="optimized_resume.tex"):
    """
    Create a LaTeX document from resume JSON using the template in latex_resume_format folder

    Parameters:
        resume_json (dict): Resume data in JSON format
        output_path (str): Output path for the LaTeX document

    Returns:
        bool: Success status
    """
    try:
        # Determine template file path
        template_dir = os.path.join(os.path.dirname(
            os.path.abspath(__file__)), "latex_resume_format")
        template_file = os.path.join(template_dir, "resume_faangpath.tex")

        # Check if template exists
        if not os.path.exists(template_file):
            print(f"Warning: Template file not found at {template_file}")
            print("Falling back to default LaTeX generation...")
            return _create_default_latex_resume(resume_json, output_path)

        # Read the template file
        with open(template_file, 'r', encoding='utf-8') as f:
            template_content = f.read()

        # Extract contact information
        name = resume_json["contact_info"].get("name", "")
        phone = resume_json["contact_info"].get("phone", "")
        location = resume_json["contact_info"].get("location", "")
        email = resume_json["contact_info"].get("email", "")
        linkedin = resume_json["contact_info"].get("linkedin", "")

        # Additional optional contact fields that may be present
        github = resume_json["contact_info"].get("github", "")
        website = resume_json["contact_info"].get("website", "")

        # Make sure all values are strings
        name = str(name) if name else "Your Name"
        phone = str(phone) if phone else ""
        location = str(location) if location else ""
        email = str(email) if email else ""
        linkedin = str(linkedin) if linkedin else ""
        github = str(github) if github else ""
        website = str(website) if website else ""

        # Escape LaTeX special characters in all fields
        name = escape_latex(name)
        phone = escape_latex(phone)
        location = escape_latex(location)
        email = escape_latex(email)
        linkedin = escape_latex(linkedin)
        github = escape_latex(github)
        website = escape_latex(website)

        # Replace name in template
        name_pattern = r'\\name\{[^}]*\}'
        template_content = re.sub(
            name_pattern, f'\\name{{{name}}}', template_content)

        # Build address block content
        address_blocks = []

        # First address block: Phone and Location
        address_line1 = []
        if phone:
            address_line1.append(phone)
        if location:
            address_line1.append(location)
        if address_line1:
            address_block1 = " \\\\ ".join(address_line1)
        else:
            address_block1 = "Phone \\\\ Location"

        # Second address block: email, LinkedIn, GitHub, website
        address_line2 = []
        if email:
            address_line2.append(f"\\href{{mailto:{email}}}{{{email}}}")
        if linkedin:
            address_line2.append(f"\\href{{{linkedin}}}{{LinkedIn}}")
        if github:
            address_line2.append(f"\\href{{{github}}}{{Github}}")
        if website:
            website_display = website.replace(
                "https://", "").replace("http://", "")
            address_line2.append(f"\\href{{{website}}}{{{website_display}}}")

        if address_line2:
            address_block2 = " \\\\ ".join(address_line2)
        else:
            address_block2 = "example@email.com"

        # Find and replace address blocks
        address_patterns = list(re.finditer(
            r'\\address\{[^}]*\}', template_content))

        if len(address_patterns) >= 2:
            # Replace first and second address blocks
            template_content = re.sub(re.escape(address_patterns[0].group(
                0)), f'\\address{{{address_block1}}}', template_content, count=1)
            template_content = re.sub(re.escape(address_patterns[1].group(
                0)), f'\\address{{{address_block2}}}', template_content, count=1)
        elif len(address_patterns) == 1:
            # Replace only first address block and add second
            template_content = re.sub(re.escape(address_patterns[0].group(
                0)), f'\\address{{{address_block1}}}\\address{{{address_block2}}}', template_content, count=1)

        # Handle sections by finding each rSection and replacing its content

        # Education Section
        education_pattern = r'\\begin\{rSection\}\{Education\}(.*?)\\end\{rSection\}'
        education_match = re.search(
            education_pattern, template_content, re.DOTALL)

        if education_match and "education" in resume_json and resume_json["education"]:
            education_content = "\n\n"
            for edu in resume_json["education"]:
                degree = escape_latex(str(edu.get("degree", "")))
                institution = escape_latex(str(edu.get("institution", "")))
                dates = escape_latex(str(edu.get("dates", "")))
                details = escape_latex(str(edu.get("details", "")))

                education_content += f"{{\\bf {degree}}}, {institution} \\hfill {{{dates}}}\\\\\n"
                if details:
                    education_content += f"\\textbf{{Relevant Coursework:}} {details}\n\n"
                else:
                    education_content += "\n"

            education_section = f"\\begin{{rSection}}{{Education}}{education_content}\\end{{rSection}}"
            template_content = template_content.replace(
                education_match.group(0), education_section)

        # Skills Section
        skills_pattern = r'\\begin\{rSection\}\{SKILLS\}(.*?)\\end\{rSection\}'
        skills_match = re.search(skills_pattern, template_content, re.DOTALL)

        if skills_match and "skills" in resume_json:
            skills_content = "\n\n\\begin{tabular}{ @{} >{\\bfseries}l @{\\hspace{6ex}} l }\n"

            if isinstance(resume_json["skills"], list):
                skills_list = [escape_latex(str(skill))
                               for skill in resume_json["skills"]]
                skills_str = ", ".join(skills_list)
                skills_content += f"Skills & {skills_str} \\\\\n"
            elif isinstance(resume_json["skills"], dict):
                for skill_category, skills in resume_json["skills"].items():
                    if skills and isinstance(skills, list):
                        # Format the category name for display
                        category_display = escape_latex(skill_category.replace(
                            "_", " ").title())
                        skills_list = [escape_latex(str(skill))
                                       for skill in skills]
                        skills_str = ", ".join(skills_list)
                        skills_content += f"{category_display} & {skills_str} \\\\\n"

            skills_content += "\\end{tabular}\\\\\n"
            skills_section = f"\\begin{{rSection}}{{SKILLS}}{skills_content}\\end{{rSection}}"
            template_content = template_content.replace(
                skills_match.group(0), skills_section)

        # Experience Section
        experience_pattern = r'\\begin\{rSection\}\{EXPERIENCE\}(.*?)\\end\{rSection\}'
        experience_match = re.search(
            experience_pattern, template_content, re.DOTALL)

        if experience_match and "experience" in resume_json and resume_json["experience"]:
            experience_content = "\n\n"

            for job in resume_json["experience"]:
                title = escape_latex(str(job.get("title", "")))
                company = escape_latex(str(job.get("company", "")))
                dates = escape_latex(str(job.get("dates", "")))
                location = escape_latex(str(job.get("location", "")))
                description = job.get("description", [])

                # Ensure description is a list of strings
                if not isinstance(description, list):
                    description = [str(description)]

                experience_content += f"\\textbf{{{title}}} \\hfill {dates}\\\\\n"
                experience_content += f"{company} \\hfill \\textit{{{location}}}\n"
                experience_content += "\\begin{itemize}\n    \\itemsep -3pt {} \n"

                for bullet in description:
                    # Ensure bullet is a string and escape LaTeX special characters
                    bullet_text = escape_latex(str(bullet))
                    experience_content += f"     \\item {bullet_text}\n"

                experience_content += "\\end{itemize}\n\n"

            experience_section = f"\\begin{{rSection}}{{EXPERIENCE}}{experience_content}\\end{{rSection}}"
            template_content = template_content.replace(
                experience_match.group(0), experience_section)

        # Projects Section
        projects_pattern = r'\\begin\{rSection\}\{PROJECTS\}(.*?)\\end\{rSection\}'
        projects_match = re.search(
            projects_pattern, template_content, re.DOTALL)

        if projects_match and "projects" in resume_json and resume_json["projects"]:
            projects_content = "\n\\vspace{-1.25em}\n"

            for project in resume_json["projects"]:
                if isinstance(project, dict):
                    title = escape_latex(str(project.get("title", "")))
                    description = project.get("description", "")
                    technologies = escape_latex(
                        str(project.get("technologies", "")))
                    url = escape_latex(str(project.get("url", "")))

                    # Add URL if available
                    if url:
                        title_with_url = f"{title} \\href{{{url}}}{{(Link)}}"
                    else:
                        title_with_url = title

                    tech_text = f" \\textbf{{- {technologies}}}" if technologies else ""
                    projects_content += f"\\item \\textbf{{{title_with_url}}}{tech_text} \n"

                    if description:
                        projects_content += "\\begin{itemize}\n    \\itemsep -6pt {} \n"
                        # Process description based on its type
                        if isinstance(description, list):
                            for bullet in description:
                                safe_bullet = escape_latex(str(bullet))
                                projects_content += f"     \\item {safe_bullet}\n"
                        else:
                            safe_description = escape_latex(str(description))
                            projects_content += f"     \\item {safe_description}\n"
                        projects_content += " \\end{itemize}\n"
                elif isinstance(project, str):
                    # If project is just a string
                    safe_project = escape_latex(project)
                    projects_content += f"\\item {safe_project}\n"

            projects_section = f"\\begin{{rSection}}{{PROJECTS}}{projects_content}\\end{{rSection}}"
            template_content = template_content.replace(
                projects_match.group(0), projects_section)

        # Activities Section
        activities_pattern = r'\\begin\{rSection\}\{Extra-Curricular Activities\}(.*?)\\end\{rSection\}'
        activities_match = re.search(
            activities_pattern, template_content, re.DOTALL)

        if activities_match and "activities" in resume_json and resume_json["activities"]:
            activities_content = "\n\\vspace{0em}\n\\begin{itemize}\n    \\itemsep -6pt {} \n"

            for activity in resume_json["activities"]:
                # Ensure activity is a string and escape LaTeX special characters
                safe_activity = escape_latex(str(activity))
                activities_content += f"     \\item {safe_activity}\n"

            activities_content += "\\end{itemize}\n"
            activities_section = f"\\begin{{rSection}}{{Extra-Curricular Activities}}{activities_content}\\end{{rSection}}"
            template_content = template_content.replace(
                activities_match.group(0), activities_section)

        # Leadership Section (optional)
        leadership_pattern = r'\\begin\{rSection\}\{Leadership\}(.*?)\\end\{rSection\}'
        leadership_match = re.search(
            leadership_pattern, template_content, re.DOTALL)

        if "leadership" in resume_json and resume_json["leadership"]:
            leadership_content = "\n\\vspace{0em}\n\\begin{itemize}\n    \\itemsep -6pt {} \n"

            for leadership in resume_json["leadership"]:
                # Ensure leadership is a string and escape LaTeX special characters
                safe_leadership = escape_latex(str(leadership))
                leadership_content += f"     \\item {safe_leadership}\n"

            leadership_content += "\\end{itemize}\n"
            leadership_section = f"\\begin{{rSection}}{{Leadership}}{leadership_content}\\end{{rSection}}"

            if leadership_match:
                template_content = template_content.replace(
                    leadership_match.group(0), leadership_section)
            else:
                # Add leadership section at the end of the document
                end_document_pos = template_content.find("\\end{document}")
                if end_document_pos > 0:
                    template_content = template_content[:end_document_pos] + "\n\n" + \
                        leadership_section + "\n\n" + \
                        template_content[end_document_pos:]

        # Handle Summary/Objective Section (uncomment if exists)
        if "% \\begin{rSection}{OBJECTIVE}" in template_content and "summary" in resume_json:
            summary_text = escape_latex(str(resume_json["summary"]))
            template_content = template_content.replace(
                "% \\begin{rSection}{OBJECTIVE}", "\\begin{rSection}{OBJECTIVE}")
            template_content = template_content.replace(
                "% \\end{rSection}", "\\end{rSection}")

            # Now find and replace the content between these tags
            objective_pattern = r'\\begin\{rSection\}\{OBJECTIVE\}(.*?)\\end\{rSection\}'
            objective_match = re.search(
                objective_pattern, template_content, re.DOTALL)

            if objective_match:
                objective_content = f"\n\n{{{summary_text}}}\n\n"
                objective_section = f"\\begin{{rSection}}{{OBJECTIVE}}{objective_content}\\end{{rSection}}"
                template_content = template_content.replace(
                    objective_match.group(0), objective_section)

        # Write the modified template to the output file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(template_content)

        # Copy resume.cls to the output directory if it doesn't exist
        output_dir = os.path.dirname(output_path)
        if output_dir == "":
            output_dir = "."

        cls_source = os.path.join(template_dir, "resume.cls")
        cls_target = os.path.join(output_dir, "resume.cls")

        try:
            if os.path.exists(cls_source) and not os.path.exists(cls_target):
                with open(cls_source, 'r', encoding='utf-8') as src:
                    with open(cls_target, 'w', encoding='utf-8') as dst:
                        dst.write(src.read())
            else:
                print(f"Note: resume.cls already exists at {cls_target}")
        except Exception as e:
            print(f"Warning: Could not copy resume.cls file: {str(e)}")
            print(
                f"You may need to manually copy resume.cls from {template_dir} to {output_dir}")

        print(
            f"✅ LaTeX resume file created at {output_path} using template format")
        print("To generate PDF, run: pdflatex optimized_resume.tex")
        return True

    except Exception as e:
        print(f"Error creating LaTeX resume from template: {str(e)}")
        print(f"Debug info - JSON keys: {list(resume_json.keys())}")
        print("Falling back to default LaTeX generation...")
        return _create_default_latex_resume(resume_json, output_path)


def escape_latex(text):
    """
    Escape LaTeX special characters in text

    Parameters:
        text (str): Text to escape

    Returns:
        str: Text with LaTeX special characters escaped
    """
    if not isinstance(text, str):
        text = str(text)

    # Define LaTeX special characters that need escaping
    special_chars = {
        '&': '\\&',
        '%': '\\%',
        '$': '\\$',
        '#': '\\#',
        '_': '\\_',
        '{': '\\{',
        '}': '\\}',
        '~': '\\textasciitilde{}',
        '^': '\\textasciicircum{}',
        '\\': '\\textbackslash{}',
        '<': '\\textless{}',
        '>': '\\textgreater{}'
    }

    # Replace each special character with its escaped version
    for char, replacement in special_chars.items():
        text = text.replace(char, replacement)

    return text

# Default LaTeX generation function for fallback


def _create_default_latex_resume(resume_json, output_path="optimized_resume.tex"):
    """
    Create a basic LaTeX document from resume JSON (fallback implementation)

    Parameters:
        resume_json (dict): Resume data in JSON format
        output_path (str): Output path for the LaTeX document

    Returns:
        bool: Success status
    """
    try:
        # Start building the LaTeX document
        latex_content = []

        # Document class and packages
        latex_content.append("\\documentclass{resume}")
        latex_content.append(
            "\\usepackage[left=0.4 in,top=0.4in,right=0.4 in,bottom=0.4in]{geometry}")
        latex_content.append(
            "\\newcommand{\\tab}[1]{\\hspace{.2667\\textwidth}\\rlap{#1}}")
        latex_content.append(
            "\\newcommand{\\itab}[1]{\\hspace{0em}\\rlap{#1}}")

        # Contact information
        name = escape_latex(
            str(resume_json["contact_info"].get("name", "Firstname Lastname")))
        latex_content.append(f"\\name{{{name}}}")

        # Contact info - first address block (phone, location)
        phone = escape_latex(str(resume_json["contact_info"].get("phone", "")))
        location = escape_latex(
            str(resume_json["contact_info"].get("location", "")))
        contact_line1 = f"{phone} \\\\ {location}"
        latex_content.append(f"\\address{{{contact_line1}}}")

        # Contact info - second address block (email, linkedin, website)
        email = escape_latex(str(resume_json["contact_info"].get("email", "")))
        linkedin = escape_latex(
            str(resume_json["contact_info"].get("linkedin", "")))
        website = escape_latex(
            str(resume_json["contact_info"].get("website", "")))

        email_line = f"\\href{{mailto:{email}}}{{{email}}}" if email else ""
        linkedin_line = f"\\href{{{linkedin}}}{{{linkedin.replace('https://', '')}}}" if linkedin else ""
        website_line = f"\\href{{{website}}}{{{website.replace('https://', '')}}}" if website else ""

        contact_parts = [part for part in [
            email_line, linkedin_line, website_line] if part]
        contact_line2 = " \\\\ ".join(
            contact_parts) if contact_parts else "example@email.com"
        latex_content.append(f"\\address{{{contact_line2}}}")

        # Begin document
        latex_content.append("\\begin{document}")

        # Objective/Summary
        summary_text = escape_latex(str(resume_json.get("summary", resume_json.get(
            "objective", "Professional seeking opportunities to apply skills and experience."))))
        latex_content.append("\\begin{rSection}{OBJECTIVE}")
        latex_content.append("")
        latex_content.append(f"{{{summary_text}}}")
        latex_content.append("")
        latex_content.append("\\end{rSection}")

        # Education
        if "education" in resume_json and resume_json["education"]:
            latex_content.append("\\begin{rSection}{Education}")
            latex_content.append("")

            for edu in resume_json["education"]:
                degree = escape_latex(str(edu.get("degree", "")))
                institution = escape_latex(str(edu.get("institution", "")))
                dates = escape_latex(str(edu.get("dates", "")))
                details = escape_latex(str(edu.get("details", "")))

                latex_content.append(
                    f"{{\\bf {degree}}}, {institution} \\hfill {{{dates}}}")
                if details:
                    latex_content.append(f"Relevant Coursework: {details}")
                latex_content.append("")

            latex_content.append("\\end{rSection}")

        # Skills
        if "skills" in resume_json:
            latex_content.append("\\begin{rSection}{SKILLS}")
            latex_content.append("")
            latex_content.append(
                "\\begin{tabular}{ @{} >{\\bfseries}l @{\\hspace{6ex}} l }")

            if isinstance(resume_json["skills"], list):
                skills_list = [escape_latex(str(skill))
                               for skill in resume_json["skills"]]
                skills_str = ", ".join(skills_list)
                latex_content.append(f"Skills & {skills_str} \\\\")
            elif isinstance(resume_json["skills"], dict):
                if "technical_skills" in resume_json["skills"]:
                    tech_skills_list = [escape_latex(
                        str(skill)) for skill in resume_json["skills"]["technical_skills"]]
                    tech_skills = ", ".join(tech_skills_list)
                    latex_content.append(
                        f"Technical Skills & {tech_skills} \\\\")
                if "soft_skills" in resume_json["skills"]:
                    soft_skills_list = [escape_latex(
                        str(skill)) for skill in resume_json["skills"]["soft_skills"]]
                    soft_skills = ", ".join(soft_skills_list)
                    latex_content.append(f"Soft Skills & {soft_skills} \\\\")
                if "other_skills" in resume_json["skills"]:
                    other_skills_list = [escape_latex(
                        str(skill)) for skill in resume_json["skills"]["other_skills"]]
                    other_skills = ", ".join(other_skills_list)
                    latex_content.append(f"Other Skills & {other_skills} \\\\")

            latex_content.append("\\end{tabular}\\\\")
            latex_content.append("\\end{rSection}")

        # Experience
        if "experience" in resume_json and resume_json["experience"]:
            latex_content.append("\\begin{rSection}{EXPERIENCE}")
            latex_content.append("")

            for job in resume_json["experience"]:
                title = escape_latex(str(job.get("title", "")))
                company = escape_latex(str(job.get("company", "")))
                dates = escape_latex(str(job.get("dates", "")))
                location = escape_latex(str(job.get("location", "")))
                description = job.get("description", [])

                latex_content.append(
                    f"\\textbf{{{title}}} \\hfill {dates}\\\\")
                latex_content.append(
                    f"{company} \\hfill \\textit{{{location}}}")
                latex_content.append("\\begin{itemize}")
                latex_content.append("    \\itemsep -3pt {} ")

                for bullet in description:
                    # Safely handle LaTeX special characters
                    safe_bullet = escape_latex(str(bullet))
                    latex_content.append(f"     \\item {safe_bullet}")

                latex_content.append("\\end{itemize}")
                latex_content.append("")

            latex_content.append("\\end{rSection}")

        # Projects
        if "projects" in resume_json and resume_json["projects"]:
            latex_content.append("\\begin{rSection}{PROJECTS}")
            latex_content.append("\\vspace{-1.25em}")

            for project in resume_json["projects"]:
                if isinstance(project, dict):
                    title = escape_latex(str(project.get("title", "")))
                    description = project.get("description", "")
                    technologies = escape_latex(
                        str(project.get("technologies", "")))
                    url = escape_latex(str(project.get("url", "")))

                    # Format project entry
                    if url:
                        title_text = f"\\textbf{{{title}}} \\href{{{url}}}{{(Link)}}"
                    else:
                        title_text = f"\\textbf{{{title}}}"

                    if technologies:
                        title_text += f" - {technologies}"

                    latex_content.append(f"\\item {title_text}")

                    # Handle description based on its type
                    if description:
                        if isinstance(description, list):
                            latex_content.append("\\begin{itemize}")
                            for bullet in description:
                                safe_bullet = escape_latex(str(bullet))
                                latex_content.append(
                                    f"    \\item {safe_bullet}")
                            latex_content.append("\\end{itemize}")
                        else:
                            safe_description = escape_latex(str(description))
                            latex_content.append(f"    {safe_description}")
                elif isinstance(project, str):
                    safe_project = escape_latex(str(project))
                    latex_content.append(f"\\item {safe_project}")

            latex_content.append("\\end{rSection}")

        # Activities (if available)
        if "activities" in resume_json and resume_json["activities"]:
            latex_content.append(
                "\\begin{rSection}{Extra-Curricular Activities}")
            latex_content.append("\\begin{itemize}")

            for activity in resume_json["activities"]:
                # Safely handle LaTeX special characters
                safe_activity = escape_latex(str(activity))
                latex_content.append(f"    \\item {safe_activity}")

            latex_content.append("\\end{itemize}")
            latex_content.append("\\end{rSection}")

        # Leadership (if available)
        if "leadership" in resume_json and resume_json["leadership"]:
            latex_content.append("\\begin{rSection}{Leadership}")
            latex_content.append("\\begin{itemize}")

            for lead_item in resume_json["leadership"]:
                # Safely handle LaTeX special characters
                safe_lead_item = escape_latex(str(lead_item))
                latex_content.append(f"    \\item {safe_lead_item}")

            latex_content.append("\\end{itemize}")
            latex_content.append("\\end{rSection}")

        # End document
        latex_content.append("\\end{document}")

        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(latex_content))

        # Also copy the resume.cls file to the output directory if it doesn't exist
        output_dir = os.path.dirname(output_path)
        if output_dir == "":
            output_dir = "."

        template_dir = os.path.join(os.path.dirname(
            os.path.abspath(__file__)), "latex_resume_format")
        cls_source = os.path.join(template_dir, "resume.cls")
        cls_target = os.path.join(output_dir, "resume.cls")

        try:
            if os.path.exists(cls_source) and not os.path.exists(cls_target):
                with open(cls_source, 'r', encoding='utf-8') as src:
                    with open(cls_target, 'w', encoding='utf-8') as dst:
                        dst.write(src.read())
        except Exception as e:
            print(f"Warning: Could not copy resume.cls file: {str(e)}")
            print(
                f"You may need to manually copy resume.cls from the latex_resume_format directory to {output_dir}")

        print(f"✅ LaTeX resume file created at {output_path}")
        print("To generate PDF, run: pdflatex optimized_resume.tex")
        return True

    except Exception as e:
        print(f"Error creating LaTeX resume: {str(e)}")
        print(f"Debug info - JSON keys: {list(resume_json.keys())}")
        return False
