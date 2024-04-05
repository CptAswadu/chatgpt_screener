# 📚 ChatGPT Article Screener Script 🤖

This script leverages the power of OpenAI's GPT-3.5 Turbo to automate the academic article screening process. It processes an XML file of articles exported from EndNote, evaluates their relevance based on PICOS criteria, and saves the results in both CSV and XML formats.

---

## 🛠 Installation & Requirements

To install the required Python packages, run the following command:

```bash
pip install -r requirements.txt
```

### 📦 Required Packages

- beautifulsoup4
- pandas
- openai
- tqdm
- tenacity

---

## 📋 Command Line Arguments

Here are the command-line arguments that the script accepts:

| Argument        | Description                                                         | Example                    |
| --------------- | ------------------------------------------------------------------- | -------------------------- |
| --xml_file    | Path to the EndNote XML file                                        | "path/to/xml/file.xml"  |
| --systemprompt| System prompt for AI role definition                                | "You are a medical researcher AI." |
| --preprompt   | Pre-prompt for role definition                                      | "You are an AI assistant..." |
| --prompt      | Main task prompt for the AI                                          | "You are given an article..." |
| --postprompt  | PICOS criteria to guide the AI                                       | "Population (P): Patients..." |
| --output      | Path to save the output file (without extension)                    | "path/to/output/file"   |
| --apikey      | Your OpenAI API key                                                 | "YOUR_API_KEY"             |
| --model       | OpenAI model to use                                                 | "gpt-3.5-turbo"            |
| --temperature | Model's temperature setting                                          | 0.0                        |
| --interval    | Time interval between API requests (in seconds)                      | 20.0                       |
| --sleep       | If "true", puts the computer to sleep after script execution        | "true"                     |

---

## ⚙ Example Usage

Here's how you can run the script:

```bash
python script.py --xml_file "path/to/xml/file.xml" --systemprompt "You are a medical researcher AI." --preprompt "You are an AI assistant..." --prompt "You are given an article..." --postprompt "Population (P): Patients..." --output "path/to/output/file" --apikey "YOUR_API_KEY" --model "gpt-3.5-turbo" --temperature 0.8 --interval 20.0 --sleep "true"
```

---

## 📄 Output Files

The script generates two output files:

- A new XML file with the ratings added.
- A CSV file with the article details, ratings, and AI responses.

---

## 📝 Additional Notes

- Make sure to replace "YOUR_API_KEY" with your actual OpenAI API key.
- The script employs exponential backoff to handle API rate limits or failures gracefully.

## 📚 Cite this Project

If you use this script in your research or project, please cite it using the following:

[![DOI](https://zenodo.org/badge/641740789.svg)](https://zenodo.org/badge/latestdoi/641740789)
