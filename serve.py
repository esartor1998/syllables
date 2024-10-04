from flask import Flask, render_template, request
from waitress import serve
from phonemizer import phonemize
from phonemizer.separator import Separator
import re
app = Flask(__name__)

SYLLABLE_SEP = '·'
WORD_SEP = ' '
SERVING_PORT = 7778

@app.route('/', methods=['GET', 'POST'])
def index():
	errors = []
	results = {}
	results['left'] = []
	results['right'] = []
	if request.method == "POST":
		try:
			input_strings = request.form['wordbox'].split('\r\n') #retrieve the text in the wordbox after POST, split into multiline

			#phonemizes the string using festival, and separates apparent syllables with our defined sep.
			phonemized = phonemize(
						input_strings,
						language='en-us',
						backend='festival',
						separator=Separator(phone=None, word=WORD_SEP, syllable=SYLLABLE_SEP),
						strip=True,
						preserve_punctuation=False,
						njobs=4) 

			total_syllables = 0
			#these two make use of the (unfortunately) very fast python splitting and joining functions to quickly count these regardless in very fast O(n)
			char_count = len(''.join(input_strings))
			word_count = len((WORD_SEP.join(input_strings)).split(WORD_SEP))
			
			#it MIGHT be faster to do this in js browser-side and just return the phonemized result, but idc rn
			#there's also the potential to vectorize this but it's not a huge deal for this application, just want this readable
			for line_num, line in enumerate(phonemized, start=1):
				#set up some per-line vars here
				line_syllables = 0
				line_words = len(line.split(WORD_SEP))
				results['left'].append(f'─── Line {line_num} ───\n')

				for word_num, word in enumerate(line.split(WORD_SEP), start=1):
					#the number of syllabes in a word are already demarcated by phonemizer! so, we just need to split & count them:
					word_syllable_count = len(word.split(SYLLABLE_SEP))
					line_syllables += word_syllable_count
					#it was important to me that "syllable" be properly pluralized sorry for the line below, and line 51
					results['left'].append(f"\tWord {word_num}, {word}:\n\t\t{word_syllable_count} {'syllable' if word_syllable_count == 1 else 'syllables'}\n")

				total_syllables += line_syllables
				results['right'].append(f"{line_syllables} {'syllable' if line_syllables == 1 else 'syllables'} in line {line_num}")

			results['right'].append(f'Total characters: {char_count}\nTotal words: {word_count}\nTotal syllable count: {total_syllables}')
			
		except Exception as e:
			print('ERR SOMEHOW',e)
			errors.append(
				f"Somehow unable to parse the form. Sorry!"
			)
	return render_template('index.html', errors=errors, results=results)

if __name__ == '__main__':
	print(f'Serving on port {SERVING_PORT}!')
	serve(app, host='127.0.0.1', port={SERVING_PORT})