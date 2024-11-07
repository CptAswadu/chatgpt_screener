import argparse
import time
import json
import re
import pandas as pd
import openai
from tqdm import tqdm
import os
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)  # for exponential backoff

# set to False if you want to use the OPENAI_API_KEY environment variable
API_KEY = False

INTERVAL: float = 20  # seconds


def parse_args():
    """
    Parse command line arguments.
    Returns:
        argparse.Namespace: The parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="""Process txt file and evaluate relevance between PICOS and articles.
        The format is as follows:
        [System Prompt]
        [ROLE DEFINITION]
        [TASK DEFINITION]
        [Article Details in JSON format]
        [PICOS in JSON format]"""
    )
    parser.add_argument("--txt_file", type=str, help="") # need to update
    parser.add_argument(
        "--systemprompt",
        type=str,
        help="system prompt such as role definition (required)",
    )
    parser.add_argument(
        "--preprompt",
        type=str,
        help="Role Definition (required)",
    )
    parser.add_argument("--prompt", type=str, help="Task Definition (required)")
    parser.add_argument(
        "--postprompt",
        type=str,
        help="PICOS (required)",
    )
    parser.add_argument(
        "--useratingfield",
        type=str,
        default="true",
        help='use rating field, default: "true"',
    )  # specific to EndNote
    parser.add_argument(
        "--ratingfield",
        type=str,
        default="custom3",
        help='field to store rating in, default: "custom3"',
    )  # specific to EndNote
    parser.add_argument(
        "--answerfield",
        type=str,
        default="custom4",
        help='field to store answer in, default: "custom4"',
    )  # specific to EndNote
    parser.add_argument("--output", type=str, help="output file name without extension")
    parser.add_argument(
        "--apikey",
        type=str,
        default=os.environ.get("OPENAI_API_KEY") or API_KEY,
        help="openai api key",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-3.5-turbo",
        help='openai model, default: "gpt-3.5-turbo"',
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.8,
        help="temperature of the model, default: 0.8",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=INTERVAL,
        help=f"time interval between requests in seconds, default: {INTERVAL:.2f}",
    )
    # sleeps the pc after completion
    parser.add_argument(
        "--sleep",
        type=str,
        default="false",
        help='sleeps the pc after completion, default: "false"',
    )
    return parser.parse_args()


def get_json(d: dict, **kwargs):
    """Get JSON format from a dictionary.

    Args:
        d (dict): dictionary to be converted to JSON format
    Returns:
        json object: JSON object
    """
    return json.dumps(d, indent=4, **kwargs)


@retry(wait=wait_random_exponential(min=1, max=30), stop=stop_after_attempt(6))
def make_request(**kwargs):
    """
    Sends a request to the OpenAI API for a chat completion.

    Args:
        **kwargs: Keyword arguments to be passed to the OpenAI API.

    Returns:
        dict: A dictionary containing the response from the OpenAI API.
    """
    c: openai.Client = kwargs.pop("client")
    return c.chat.completions.create(**kwargs)


def get_content(args, article):
    """
    Preprocesses the text before sending it to the API and returns the system prompt and content.

    Args:
        args (argparse.Namespace): The parsed command-line arguments.
        article (dict): The article to be classified.

    Returns:
        tuple: A tuple containing the system prompt and content.
    """
    prompt: str = args.prompt
    preprompt: str = args.preprompt
    postprompt: str = args.postprompt
    systemprompt: str = args.systemprompt
    # replace all '\\n' instances with '\n'
    systemprompt = systemprompt.replace("\\n", "\n")
    preprompt = "\n[ROLE]\n" + preprompt.replace("\\n", "\n")
    prompt = "\n[TASK]\n" + prompt.replace("\\n", "\n")
    # we need to convert postprompt to json
    postprompt = (
        "\n[PICOS]\n"
        + get_json({"PICOS": postprompt.replace("\\n", ", ")})
        + "\n[YOUR ANSWER IN VALID JSON FORMAT]"
    )
    article_json = "\n[ARTICLE]\n" + get_json(article)
    content = f"{preprompt}\n{prompt}\n{article_json}\n{postprompt}"
    return systemprompt, content


args = parse_args()
client = openai.OpenAI(api_key=args.apikey)

def parse_txt_file(txt_file_path):
    articles = []
    
    # Read the txt file
    with open(txt_file_path, "r", encoding="utf-8") as f:
        txt_data = f.read()

    # Extract relevant information using regular expressions
    name_match = re.search(r"'Name': '(.+?)'", txt_data)
    pmid_match = re.search(r"'PMID': '(\d+)'", txt_data)
    pmcid_match = re.search(r"'PMCID': '(\S+)'", txt_data)
    selection_criteria_match = re.search(r"'Selection_criteria': '(.+?)'", txt_data)
    clinical_questions_match = re.search(r"'Clinical_questions': '(.+?)'", txt_data)
    
     # Updated regex to capture numbers in Excluded Studies and Included Studies across multiple lines
    excluded_studies_match = re.search(r"'Excluded_studies':\s*\[(.*?)\]", txt_data, re.DOTALL)
    included_studies_match = re.search(r"'Included_studies':\s*\[(.*?)\]", txt_data, re.DOTALL)
    
    # Extract numbers from Excluded Studies and Included Studies
    excluded_studies = re.findall(r"\d+", excluded_studies_match.group(1)) if excluded_studies_match else []
    included_studies = re.findall(r"\d+", included_studies_match.group(1)) if included_studies_match else []
    
    # Extracting Excluded Studies Characteristics
    excluded_characteristics_match = re.search(r"'Excluded_Studies_characteristics': \{(.*?)\}", txt_data, re.DOTALL)
    excluded_studies_characteristics = {}
    if excluded_characteristics_match:
        characteristics_data = excluded_characteristics_match.group(1)
        # Match each entry in the characteristics dictionary
        characteristics_entries = re.findall(r"'(\d+)': '(.+?)'", characteristics_data)
        for study_id, characteristic in characteristics_entries:
            excluded_studies_characteristics[study_id] = characteristic

    # Parse extracted data
    article = {
        "Name": name_match.group(1) if name_match else "[n/a]",
        "PMID": pmid_match.group(1) if pmid_match else "[n/a]",
        "PMCID": pmcid_match.group(1) if pmcid_match else "[n/a]",
        "Selection Criteria": selection_criteria_match.group(1) if selection_criteria_match else "[n/a]",
        "Clinical Questions": clinical_questions_match.group(1) if clinical_questions_match else "[n/a]",
        "Excluded Studies": excluded_studies,
        "Included Studies": included_studies,
        "Excluded Studies Characteristics": excluded_studies_characteristics
    }

    articles.append(article)
    
    return articles


answers = []
ratings = []
for i, article in tqdm(
    enumerate(articles),
    total=len(articles),
    desc="Rating Articles",
    unit="articles",
    ncols=120,
    bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}{postfix}]",
    colour="green",
):
    # assemble the content to be sent to the API
    systemprompt, content = get_content(args, article)
    # Make the API request
    try:
        response = make_request(
            client=client,
            model=args.model,
            messages=[
                {"role": "system", "content": systemprompt},
                {
                    "role": "user",
                    "content": content,
                },
            ],
            temperature=args.temperature,
        )
        answer = response.choices[0].message.content
        # since the answer is in json format, we need to convert it back to a dictionary
        answer = json.loads(answer)
        rating = answer["rating"]
        answer = answer["answer"]

    except Exception as ex:
        print(f"Exception: {ex}")
        answers.append("error")
        ratings.append("error")
        continue

    print(f'\nContent:\n"{content}"\nAnswer:\n"{answer}"\nRating: {rating}\n')
    answers.append(answer)
    ratings.append(rating)
    # Delay to avoid exceeding the API rate limit
    if i < len(articles) - 1:
        time.sleep(args.interval)


# Append 'Rating' and 'Answer' to each article dictionary in the `articles` list
for i, article in enumerate(articles):
    if args.useratingfield.lower() == "true":
        # Add a new field for rating
        article[args.ratingfield] = str(ratings[i]) if i < len(ratings) else "[n/a]"

    # Add a new field for answer
    article[args.answerfield] = str(answers[i]) if i < len(answers) else "[n/a]"

# Convert articles to a DataFrame
results = pd.DataFrame(articles)

# If using ratings, add them as a separate column
if args.useratingfield.lower() == "true":
    results["Rating"] = ratings
results["Answer"] = answers

# Set the output path, stripping file extension if present
outfilepath = args.output
if "." in args.output:
    outfilepath = args.output[: args.output.rfind(".")]

try:
    # Save as CSV file
    results.to_csv(outfilepath + ".csv", index=False)
    print(f"Results saved to {outfilepath}.csv")
except OSError:
    print("An error occurred during saving.\nSaving to relative path...")
    results.to_csv("newfile.csv", index=False)
    print("Results saved to newfile.csv")

# Optionally put the system to sleep on Windows
if args.sleep.lower() == "true" and os.name == "nt":
    os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")