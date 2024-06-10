import json
import csv

file = open('/Users/max/Downloads/JEOPARDY_QUESTIONS1.json')
data = json.loads(file.read())

outfile = open('/Users/max/Code/triviabot/questions.csv', 'w')
writer = csv.writer(outfile)

def fix(s):
	s = "".join([c for c in s if c.isprintable()])
	
	return s

for item in data:
	category = fix(item['category'])
	question = fix(item['question'])
	answer = fix(item['answer'])

	if question[0] == question[-1] == "'":
		question = question.strip("'")

	formatted_question = f"{category} {question}"
	writer.writerow([formatted_question,answer])
