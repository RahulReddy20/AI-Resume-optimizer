#!/usr/bin/env python
import os
import argparse
import sys
import json
import subprocess
import platform
from pdf_parser import extract_json_from_pdf, read_job_description, extract_text_from_pdf
from utils import calculate_similarity, identify_missing_skills
from resume_generator import generate_optimized_resume, create_resume_docx, create_resume_latex


def find_pdflatex():
    """Find pdflatex executable in common installation locations"""
    # Default search in PATH
    try:
        subprocess.run(['pdflatex', '--version'],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        return 'pdflatex'
    except FileNotFoundError:
        pass

    # Check common MiKTeX installation paths on Windows
    if platform.system() == 'Windows':
        common_paths = [
            r'C:\Program Files\MiKTeX\miktex\bin\x64\pdflatex.exe',
            r'C:\Program Files (x86)\MiKTeX\miktex\bin\pdflatex.exe',
            r'C:\Users\{}\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe'.format(
                os.getenv('USERNAME')),
            r'C:\MiKTeX\miktex\bin\x64\pdflatex.exe'
        ]

        for path in common_paths:
            if os.path.exists(path):
                return path

    # Common MacOS TeXLive/MacTeX paths
    elif platform.system() == 'Darwin':
        common_paths = [
            '/Library/TeX/texbin/pdflatex',
            '/usr/local/texlive/bin/pdflatex'
        ]

        for path in common_paths:
            if os.path.exists(path):
                return path

    # Not found
    return None


def generate_pdf_from_latex(latex_file, pdflatex_path=None):
    """Generate PDF from LaTeX file using pdflatex"""
    if not pdflatex_path:
        pdflatex_path = find_pdflatex()

    if not pdflatex_path:
        print("Error: pdflatex not found. Cannot generate PDF directly.")
        print("Please check your LaTeX installation and ensure pdflatex is in your PATH.")
        return False

    try:
        # Run pdflatex twice to resolve references
        for _ in range(2):
            result = subprocess.run(
                [pdflatex_path, '-interaction=nonstopmode', latex_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

        # Check if PDF was created
        pdf_file = latex_file.replace('.tex', '.pdf')
        if os.path.exists(pdf_file):
            return True
        else:
            print("Error generating PDF. pdflatex output:")
            print(result.stdout)
            print(result.stderr)
            return False

    except Exception as e:
        print(f"Error running pdflatex: {str(e)}")
        return False


def main():
    """Main function to run the resume optimizer"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="AI Resume Optimizer that tailors resumes to job descriptions")
    parser.add_argument("--resume", required=True,
                        help="Path to the resume PDF file")
    parser.add_argument("--job_description", required=True,
                        help="Job description text or path to job description file")
    parser.add_argument("--output", default=None,
                        help="Output file path (without extension, default: optimized_resume)")
    parser.add_argument("--format", default=None, choices=["pdf", "docx"],
                        help="Output format (default: pdf)")
    parser.add_argument("--debug", action="store_true",
                        help="Save intermediate JSON for debugging")

    args = parser.parse_args()

    # Set format default
    if args.format is None:
        args.format = "pdf"
        print(f"No format specified. Using {args.format} format.")

    # Find pdflatex
    pdflatex_path = find_pdflatex() if args.format == "pdf" else None

    # Set default output path based on format if not provided
    if args.output is None:
        args.output = "optimized_resume"

    # Remove extension if provided
    args.output = os.path.splitext(args.output)[0]

    try:
        # Step 1: Extract text from resume PDF
        print("Extracting text from resume...")
        resume_json = extract_json_from_pdf(args.resume)
        resume_text = extract_text_from_pdf(args.resume)
        with open("resume_text.txt", "w", encoding="utf-8") as f:
            f.write(resume_text)
        if not resume_json:
            print("Error: Could not extract text from resume PDF. Please check the file.")
            return 1

        # Step 2: Read job description
        print("Reading job description...")
        job_description = read_job_description(args.job_description)

        if not job_description:
            print("Error: Could not read job description. Please check the input.")
            return 1

        # Step 3: Analyze similarity
        print("Analyzing similarity between resume and job description...")
        similarity_score = calculate_similarity(resume_text, job_description)
        print(f"Current match score: {similarity_score:.2f} out of 1.00")

        # Step 4: Identify missing skills
        print("Identifying missing skills...")
        missing_skills = identify_missing_skills(job_description, resume_text)
        if missing_skills:
            print("Missing skills/keywords:", ", ".join(missing_skills))
        else:
            print("No major missing skills identified.")

        # Step 5: Generate optimized resume
        print("Generating optimized resume...")
        optimized_resume_json = generate_optimized_resume(
            resume_json,
            job_description,
            missing_skills,
            similarity_score
        )

        if not optimized_resume_json:
            print("Error: Failed to generate optimized resume.")
            return 1

        # Save JSON for debugging if requested
        if args.debug:
            debug_file = f"{args.output}.json"
            print(f"Saving debug JSON to {debug_file}")
            with open(debug_file, 'w', encoding='utf-8') as f:
                json.dump(optimized_resume_json, f, indent=2)
            print(f"Available fields: {list(optimized_resume_json.keys())}")

        # Step 6: Create output document
        if args.format == "pdf":
            # Generate LaTeX first
            print("Creating LaTeX document...")
            latex_file = f"{args.output}.tex"
            latex_success = create_resume_latex(
                optimized_resume_json, latex_file)

            if not latex_success:
                print("Error: Failed to create LaTeX document.")
                return 1

            # Then convert to PDF
            print("Generating PDF from LaTeX...")
            if pdflatex_path:
                pdf_success = generate_pdf_from_latex(
                    latex_file, pdflatex_path)
                if pdf_success:
                    print(
                        f"✅ Optimized resume saved successfully to: {args.output}.pdf")
                    return 0
                else:
                    print("Failed to generate PDF directly. Manual steps:")
                    print("\n1. MiKTeX might be installed but not in your PATH.")
                    print("2. Try running pdflatex from MiKTeX Console:")
                    print("   - Open MiKTeX Console (search in Start menu)")
                    print(
                        "   - Go to Settings -> Directories and note the installation path")
                    print(
                        "   - The pdflatex.exe is usually in 'bin' or 'miktex/bin/x64' subfolder")
                    print(
                        f"3. Try running manually with full path: C:\\path\\to\\pdflatex.exe {latex_file}")
                    print(
                        "\nAlternatively, open the .tex file with a LaTeX editor like TeXworks (comes with MiKTeX)")
                    print(f"LaTeX file saved to: {latex_file}")
                    return 1
            else:
                print(
                    "LaTeX is not installed or not found in PATH. PDF generation requires LaTeX.")
                print(
                    "The LaTeX file has been saved - you can convert it later after installing LaTeX.")
                print("\nTo install LaTeX:")
                print("- Windows: Install MiKTeX from https://miktex.org/download")
                print("- macOS: Install MacTeX from https://www.tug.org/mactex/")
                print("- Linux: Run 'sudo apt-get install texlive-full'")
                print(f"\nLaTeX file saved to: {latex_file}")
                return 1
        else:  # docx
            docx_file = f"{args.output}.docx"
            print(f"Creating Word document: {docx_file}...")
            success = create_resume_docx(optimized_resume_json, docx_file)
            if success:
                print(f"✅ Optimized resume saved successfully to: {docx_file}")
                return 0
            else:
                print("Error: Failed to create Word document.")
                return 1

    except Exception as e:
        print(f"Error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
