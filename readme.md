# ChatGPT Article Screener (Official implementation)
## Required packages
argparse, bs4, pandas, openai, tqdm
## Sample arguments
- **output**: "path/to/output/file"
- **xml_file**: "path/to/input/xml"

- **systemprompt**: "You are a medical researcher AI."

- **preprompt**: "You are an AI assistant for medical research conducting article screening for inclusion in a systematic review."

- **prompt**: "You are given an article and PICOS in JSON format.\\nYour response must be concise and in JSON format containing these key/values:\\nanswer: [how the article is or is not relevant to the PICOS],\\nrating: [relevance rating number in integer form ranging from 1 (least relevance) to 5 (most relevance)]"

- **postprompt**: "Population (P): Patients with known or suspected vasculitis.\\nIntervention (I): magnetic resonance (MR) imaging\\nComparator (C): other imaging modalities\\nOutcomes (O): diagnostic efficacy metrics\\nStudy design (S): diagnostic efficacy studies"

- **model**: "gpt-3.5-turbo"
- **apikey**: "YOUR_API_KEY"
- **interval**: 20
- **temperature**: 0.0
-  **ratingfield**: "custom3"
-  **useratingfield**: true
-  **answerfield**: "custom4"
-  **sleep**: false

### **Note**: 
Since the terminal does not support breaks (\r\n), use \\n instead.

### Example command prompt:
~~~bash
path\to\python.exe "path\to\classifier_script.py" --xml_file "path\to\endnote\export.xml" --systemprompt "You are a medical researcher AI." --preprompt "You are an AI assistant for medical research conducting article screening for inclusion in a systematic review." --prompt "You are given an article and PICOS in JSON format.\nYour response must be concise and in JSON format containing these key/values:\nanswer: [how the article is or is not relevant to the PICOS],\nrating: [relevance rating number in integer form ranging from 1 (least relevance) to 5 (most relevance)]" --postprompt "Population (P): Patients with known or suspected vasculitis.\nIntervention (I): magnetic resonance (MR) imaging\nComparator (C): other imaging modalities\nOutcomes (O): diagnostic efficacy metrics\nStudy design (S): diagnostic efficacy studies" --useratingfield "true" --ratingfield "custom3" --answerfield "custom4" --output "path\to\output\file" --apikey "YOUR_API_KEY" --model "gpt-3.5-turbo" --temperature 0.0 --interval 20
~~~
