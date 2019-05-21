import datetime
from logger_tpl_diff.util import run
from flask import Flask, render_template, request

app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if request.form.get('time') == datetime.datetime.now().strftime('%Y-%m-%d'):
            r = run(request.form.get('arg'))
        else:
            r = run(request.form.get('arg'), request.form.get('time'))
        return render_template('res.html', data=sorted(r, key=lambda x: x['time'], reverse=True))
    current_time = datetime.datetime.now()
    min_time = current_time - datetime.timedelta(days=7)
    return render_template('index.html', current_time=current_time.strftime('%Y-%m-%d'),
                           max_time=current_time.strftime('%Y-%m-%d'), min_time=min_time.strftime('%Y-%m-%d'))


if __name__ == '__main__':
    app.run('0.0.0.0', 9999)
