from logger_tpl_diff.util import run
from flask import Flask, render_template, request


app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        r = run(request.form.get('arg'))
        return render_template('res.html', data=sorted(r, key=lambda x:x['time'], reverse=True))
    return render_template('index.html')


if __name__ == '__main__':
    app.run('0.0.0.0', 9999)