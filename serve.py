from flask import Flask, render_template, request, flash
from flask_wtf import FlaskForm
from wtforms import TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length
from waitress import serve
from phonemizer import phonemize
from phonemizer.separator import Separator
import logging

# ----- Configuration -----
SYLLABLE_SEP = '·'
WORD_SEP = ' '
SERVING_PORT = 7778
MAX_INPUT_LENGTH = 5000  # max characters to prevent DoS

app = Flask(__name__)
app.secret_key = 'replace_with_a_secure_random_secret!'  # Needed for CSRF protection

# ----- Logging -----
logging.basicConfig(
    filename='app.log', level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)

# ----- Flask-WTF Form -----
class WordForm(FlaskForm):
    wordbox = TextAreaField('Words', validators=[
        DataRequired(message="Please enter some text."),
        Length(max=MAX_INPUT_LENGTH, message=f"Input cannot exceed {MAX_INPUT_LENGTH} characters.")
    ])
    submit = SubmitField('Phonemize')

# ----- Routes -----
@app.route('/', methods=['GET', 'POST'])
def index():
    form = WordForm()
    results = {'left': [], 'right': []}

    if form.validate_on_submit():
        try:
            # Split multiline input
            input_strings = form.wordbox.data.splitlines()

            # Phonemize using Festival backend
            phonemized = phonemize(
                input_strings,
                language='en-us',
                backend='festival',
                separator=Separator(phone=None, word=WORD_SEP, syllable=SYLLABLE_SEP),
                strip=True,
                preserve_punctuation=False,
                njobs=4
            )

            total_syllables = 0
            char_count = len(''.join(input_strings))
            word_count = len((WORD_SEP.join(input_strings)).split(WORD_SEP))

            for line_num, line in enumerate(phonemized, start=1):
                line_syllables = 0
                line_words = len(line.split(WORD_SEP))
                results['left'].append(f'─── Line {line_num} ───\n')

                for word_num, word in enumerate(line.split(WORD_SEP), start=1):
                    word_syllable_count = len(word.split(SYLLABLE_SEP))
                    line_syllables += word_syllable_count
                    results['left'].append(
                        f"\tWord {word_num}, {word}:\n\t\t{word_syllable_count} {'syllable' if word_syllable_count == 1 else 'syllables'}\n"
                    )

                total_syllables += line_syllables
                results['right'].append(f"{line_syllables} {'syllable' if line_syllables == 1 else 'syllables'} in line {line_num}")

            results['right'].append(f'Total characters: {char_count}\nTotal words: {word_count}\nTotal syllable count: {total_syllables}')

        except Exception as e:
            logging.exception("Error during phonemization")  # Logs full traceback safely
            flash("An error occurred while processing your input. Please try again.", "danger")

    elif request.method == 'POST':
        # Form did not validate
        for field, errors in form.errors.items():
            for error in errors:
                flash(error, "danger")

    return render_template('index.html', form=form, results=results)

# ----- Main -----
if __name__ == '__main__':
    logging.info(f"Starting server on port {SERVING_PORT}")
    serve(app, host='127.0.0.1', port=SERVING_PORT)

