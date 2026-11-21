# Prompt Engineering for Simplifying Complex Medical Reports
### A Patient-Friendly Approach with Smart Attention Classification

## 1. Project Overview

The Medical Report Simplifier is an AI-powered application designed to make complex medical reports easier for ordinary people to understand.

Medical reports often contain technical terms, abbreviations, test values, and reference ranges that patients may find difficult to understand.

This project uses Prompt Engineering and Google's Gemini AI to convert complex medical information into simple, patient-friendly explanations.

It also includes a Smart Attention Classification feature that identifies test results as Within Range, Attention, Critical, or Unknown.

## 2. Problem Statement

Many patients find it difficult to understand their medical reports because they contain complicated medical terminology and technical information.

This can lead to confusion and difficulty identifying which test results require attention.

Therefore, there is a need for a system that simplifies medical reports and presents important information in an understandable format.

## 3. Objectives

- Simplify complex medical reports using AI.
- Convert medical terminology into easy-to-understand language.
- Extract important test names, values, and reference ranges.
- Classify medical test results based on available information.
- Highlight results that may require attention.
- Help patients understand their reports and prepare questions for healthcare professionals.

## 4. Novelty

- **Smart Attention Classification:** result categories are decided by a deterministic, rule-based module, not by the AI model.
- **Two-stage pipeline:** the AI first extracts structured data, code classifies it, and a second prompt writes the explanation, so original values stay intact.
- **Safety-constrained prompts:** the AI is forbidden from changing values, inventing reference ranges, diagnosing or prescribing.
- **Adjustable reading level:** Very Simple, Simple or Standard explanations.
- **Patient-centred output:** glossary, questions to ask the doctor and a final takeaway.
- **Resilience:** automatic retry and fallback between Gemini models.

## 5. Technologies Used

- **Python:** Main programming language.
- **Streamlit:** Used to create the web application.
- **Google Gemini API:** Used for AI-powered medical report simplification and information extraction.
- **Prompt Engineering:** Used to guide the AI to generate simple and structured explanations.
- **PyPDF:** Used to extract text from PDF medical reports.

## 6. Project Structure

```text
Medical_Report_Simplifier1/
│
├── app.py
├── medical_extractor.py
├── gemini_helper.py
├── classifier.py
├── requirements.txt
├── README.md
│
└── .streamlit/
    └── secrets.toml
```

### Description of Files

- **app.py:** Main application file that handles PDF uploads, displays simplified reports, and presents classifications.
- **medical_extractor.py:** Extracts medical test information from uploaded reports using Gemini AI.
- **gemini_helper.py:** Generates simplified explanations of medical reports.
- **classifier.py:** Classifies test results into different attention categories.
- **requirements.txt:** Contains the Python libraries required for the project.
- **secrets.toml:** Stores the Gemini API key securely.

## 7. Smart Attention Classification

The application classifies medical test results into four categories:

| Category | Meaning |
|---|---|
| Within Range | The result falls within the provided reference range. |
| Attention | The result is marked high or low, or falls outside the reference range. |
| Critical | The report explicitly marks the result as critical. |
| Unknown | There is insufficient information to classify the result. |

The classification is based on the available test values, reference ranges, and flags in the report.

## 8. Working Procedure

1. The user uploads a medical report in PDF format.
2. The application extracts text from the uploaded PDF.
3. Gemini AI extracts important medical test information.
4. The extracted test values are passed to the classification module.
5. Each test result is assigned an attention category.
6. Gemini AI simplifies the medical information using prompt engineering.
7. The application displays the simplified report and classifications.
8. The user can download the generated report.

## 9. Installation and Execution

### Step 1: Install Python

Install Python on your computer if it is not already installed.

### Step 2: Open the Project Folder

Open the project folder in Visual Studio Code.

### Step 3: Install Required Libraries

Open the terminal and execute:

```bash
pip install -r requirements.txt
```

### Step 4: Configure the Gemini API Key

Create a `.streamlit` folder if it does not already exist.

Inside it, create a file named `secrets.toml`.

Add this line (use your own key): `GEMINI_API_KEY = "your-key-here"`

Do not share your API key publicly.

### Step 5: Run the Application

Execute the following command in the terminal:

```bash
python -m streamlit run app.py
```

The application will open in your web browser.

## 10. Results

The application successfully performs the following functions:

- Accepts medical reports in PDF format.
- Extracts important medical test information.
- Generates simplified explanations using Gemini AI.
- Classifies test results into four attention categories.
- Displays patient-friendly information.
- Allows users to download the simplified report.

The application was tested using sample medical reports containing normal results, abnormal results, and missing reference ranges.

## 11. Limitations

- The application works with text-based PDF reports.
- Accuracy depends on the quality and readability of the uploaded report.
- AI-generated explanations may not always be completely accurate.
- Missing or unclear reference ranges may result in an Unknown classification.
- The application does not diagnose diseases or prescribe treatments.

## 12. Future Enhancements

- Support for scanned medical reports using OCR.
- Support for additional medical report formats.
- Improved extraction accuracy.
- Multilingual explanations.
- Enhanced patient-friendly interface.

## 13. Conclusion

The Medical Report Simplifier demonstrates how Prompt Engineering and Artificial Intelligence can make complex medical information easier to understand.

By combining AI-powered report simplification with Smart Attention Classification, the application helps patients understand their medical reports more easily and identify results that may require discussion with healthcare professionals.

**Disclaimer:** This application is developed for educational purposes. It is not a substitute for professional medical advice, diagnosis, or treatment.