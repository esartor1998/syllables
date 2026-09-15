import os
from flask import Flask, render_template, request, flash
from flask_wtf import FlaskForm
from wtforms import TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length
from waitress import serve
from phonemizer import phonemize
from phonemizer.separator import Separator
from dotenv import load_dotenv
import logging

load_dotenv()

# ---- configuration ----
SYLLABLE_SEP = '·'
WORD_SEP = ' '
SERVING_PORT = 7778
MAX_INPUT_LENGTH = 5000  # max characters to prevent DoS

SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY is not set. Add it to a .env file (see .env.example) "
        "or export it as an environment variable."
    )

app = Flask(__name__)
app.secret_key = SECRET_KEY  # flask-wtf signs CSRF tokens with this
# the wordbox validator below caps input at MAX_INPUT_LENGTH, but that check
# only runs after flask has buffered the whole request body, so this cap is
# what stops an oversized upload before that point
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024

# ---- logging ----
logging.basicConfig(
    filename='app.log', level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)

# ---- flask-wtf form ----
class WordForm(FlaskForm):
    wordbox = TextAreaField('Words', validators=[
        DataRequired(message="Please enter some text."),
        Length(max=MAX_INPUT_LENGTH, message=f"Input cannot exceed {MAX_INPUT_LENGTH} characters.")
    ])
    submit = SubmitField('Phonemize')

# ---- routes ----
@app.route('/', methods=['GET', 'POST'])
def index():
    form = WordForm()
    results = {'left': [], 'right': []}

    if form.validate_on_submit():
        try:
            input_strings = form.wordbox.data.splitlines()

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
            # we log the full traceback server-side instead of showing it to
            # the user, so a phonemizer failure can't leak internals to them
            logging.exception("Error during phonemization")
            flash("An error occurred while processing your input. Please try again.", "danger")

    elif request.method == 'POST':
        # form did not validate
        for field, errors in form.errors.items():
            for error in errors:
                flash(error, "danger")

    return render_template('index.html', form=form, results=results, max_input_length=MAX_INPUT_LENGTH)

# ---- main ----
if __name__ == '__main__':
    logging.info(f"Starting server on port {SERVING_PORT}")
    serve(app, host='127.0.0.1', port=SERVING_PORT)

