import csv
import re
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
import warnings

warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

N_OF_REGEX = re.compile("[0-9] of ")

infile = open('/Users/max/Code/triviabot/questions.csv', 'r')
outfile = open('/Users/max/Code/triviabot/questions2.csv', 'w')
reader = csv.reader(infile)
writer = csv.writer(outfile)


def too_many_parens(answer):
    return answer.count("(") >= 2


def remove_quotes(answer):
    return answer.replace('"', '')


def remove_backslashes(answer):
    return answer.replace('\\', '')


def remove_parens(answer):
    first_lparen = answer.find("(")
    first_rparen = answer.find(")")
    if first_lparen == -1 or first_rparen == -1:
        return answer

    if first_lparen > first_rparen:
        return answer

    return answer[:first_lparen] + answer[first_rparen+1:]


def has_link(question):
    return question.lower().find("<a href=") != -1


def mentions_clue_crew(question):
    return question.lower().find("clue crew") != -1


def should_delete(question, answer):
    if has_link(question) and not mentions_clue_crew(question):
        return True

    if too_many_parens(question):
        return True

    if N_OF_REGEX.match(answer):
        return True

    return False


def remove_html_tags(question):
    return BeautifulSoup(question, "lxml").get_text()


delete_count = 0
for question, answer in reader:
    if should_delete(question, answer):
        delete_count += 1
        continue
    # continue

    question = remove_html_tags(question)
    question = question.strip()

    answer = remove_parens(answer)
    answer = remove_backslashes(answer)
    answer = remove_quotes(answer)
    answer = answer.strip()

    writer.writerow([question,answer])

print(delete_count)
