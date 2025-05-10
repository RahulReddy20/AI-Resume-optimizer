# AI Resume Optimizer

This tool analyzes your resume and a job description to create a tailored resume that better matches the job requirements.

## Setup

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Download required NLTK data:
   ```
   python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"
   ```
4. Download required spaCy model:
   ```
   python -m spacy download en_core_web_md
   ```
5. Create a `.env` file with your Google API key:

   ```
   GOOGLE_API_KEY=your_api_key_here
   ```

   You can get your API key from [Google AI Studio](https://aistudio.google.com/app/apikey)

6. For PDF output (the default format), install LaTeX:

   - **Windows**: Install [MiKTeX](https://miktex.org/download)
   - **macOS**: Install [MacTeX](https://www.tug.org/mactex/)
   - **Linux**: Run `sudo apt-get install texlive-full`

   **Note for Windows users**: After installing MiKTeX, you may need to restart your computer for the `pdflatex` command to be recognized.

## Usage

Run the main script:

```
python resume_optimizer.py --resume path/to/your/resume.pdf --job_description "Paste job description here or provide a text file path"
```

### Output Formats

The tool supports two output formats:

#### 1. PDF (Default)

PDF is the default output format. This gives you a professional-looking resume that's ready to use:

```
python resume_optimizer.py --resume resume.pdf --job_description "Job description" --format pdf
```

Even if pdflatex isn't found in your PATH, the program will:

1. Generate the LaTeX file
2. Attempt to find pdflatex in common installation locations
3. Provide detailed instructions if it can't generate the PDF directly

#### 2. Microsoft Word (.docx)

Word format can be specified with:

```
python resume_optimizer.py --resume resume.pdf --job_description "Job description" --format docx
```

### Troubleshooting LaTeX/PDF Generation

If you installed MiKTeX but still get an error about `pdflatex` not being found:

1. **Check if MiKTeX was properly installed**

   - Open the Start menu and search for "MiKTeX Console"
   - If it opens, MiKTeX is installed but not in your PATH

2. **Add MiKTeX to your PATH manually**

   - Open MiKTeX Console
   - Go to Settings → Directories to find the installation directory
   - Add the bin folder (usually `C:\Program Files\MiKTeX\miktex\bin\x64\`) to your PATH:
     1. Search for "Environment Variables" in Windows search
     2. Click "Edit the system environment variables"
     3. Click "Environment Variables..." button
     4. Under "System Variables", find "Path", select it and click "Edit"
     5. Click "New" and add the MiKTeX bin path
     6. Click "OK" on all dialogs
   - Restart your terminal/command prompt

3. **Convert the .tex file manually**
   - Open the generated .tex file with TeXworks (comes with MiKTeX)
   - Click the "pdfLaTeX" button to generate the PDF

### Debugging Issues

If you encounter problems, use the `--debug` flag to save the JSON data for inspection:

```
python resume_optimizer.py --resume resume.pdf --job_description "Job description" --debug
```
