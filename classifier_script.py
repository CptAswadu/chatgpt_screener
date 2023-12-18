import argparse
import time

# we want to work with json format
import json
from bs4 import BeautifulSoup
import pandas as pd
import openai
from tqdm import tqdm
import os
from flask import cli


from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)  # for exponential backoff

# set to False if you want to use the OPENAI_API_KEY environment variable
API_KEY = False

INTERVAL: float = 0.1  # seconds


def parse_args():
    """
    Parse command line arguments.
    Returns:
        argparse.Namespace: The parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="""Process XML file and evaluate relevance between PICOS and articles.
        The format is as follows:
        [System Prompt]
        [ROLE DEFINITION]
        [TASK DEFINITION]
        [Article Details in JSON format]
        [PICOS in JSON format]"""
    )
    parser.add_argument("--xml_file", type=str, help="path to EndNote XML file")
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

# read the xml file exported from EndNote
with open(args.xml_file, "r", encoding="utf-8") as f:
    xml_data = f.read()

# parse the xml file
soup = BeautifulSoup(xml_data, "xml")
articles = []  # empty array for storing articles

# iterate over each record and extract the title, abstract, reference type and year
for record in soup.find_all("record"):
    if record.find("titles").find("title"):
        title = record.find("titles").find("title").text
    else:
        title = "[n/a]"

    if record.find("abstract"):
        abstract = record.find("abstract").text
    else:
        abstract = "[n/a]"

    if record.find("ref-type"):
        ref_type = record.find("ref-type")["name"]
    else:
        ref_type = "[n/a]"

    if record.find("dates").find("year"):
        year = record.find("dates").find("year").text
    else:
        year = "[n/a]"

    articles.append(
        {
            "Title": title,
            "Abstract": abstract,
            "Published year": year,
            "Reference type": ref_type,
        }
    )


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

# save the new xml file with the ratings added
# create a new BeautifulSoup object with the original XML data
new_soup = BeautifulSoup(xml_data, "xml")

# find all the article records in the XML data
article_records = new_soup.find_all("record")

# loop through each article and add the rating and the answer as a new tag
for i, record in enumerate(article_records):
    if args.useratingfield.lower() == "true":
        # create a new 'custom3' tag (the default is 'custom3')
        rating_tag = new_soup.new_tag(args.ratingfield)
        rating = ratings[i]  # get the rating for this article
        rating_tag.string = str(rating)  # set the text of the tag to the rating
        record.append(rating_tag)  # add the new tag to the article record

    # create a new 'custom4' tag for the answer (the default is 'custom4')
    answer_tag = new_soup.new_tag(args.answerfield)
    ans = answers[i]  # get the answer for this article
    answer_tag.string = str(ans)  # set the text of the tag to the answer

    record.append(answer_tag)  # add the new tag to the article record

# create a dataframe from the articles
results = pd.DataFrame(articles)
if args.useratingfield.lower() == "true":
    results["Rating"] = ratings
results["Answer"] = answers
# save the modified XML data to a new file
# strip the output file of any file extensions
outfilepath = args.output
if "." in args.output:
    outfilepath = args.output[: args.output.rfind(".")]
try:
    with open(outfilepath + ".xml", "w", encoding="utf-8") as f:
        f.write(str(new_soup))
    results.to_csv(outfilepath + ".csv")
    print(f"results saved to {outfilepath}.csv and xml.")
except OSError:
    print("an error occured during saving.\nsaving to relative path...")
    with open("newfile.xml", "w", encoding="utf-8") as f:
        f.write(str(new_soup))
    results.to_csv("newfile.csv")
    print("results saved to newfile.")

if args.sleep.lower() == "true":
    os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
