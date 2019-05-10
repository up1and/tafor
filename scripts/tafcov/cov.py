import os
import sys

from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from tafor.models import db, Taf

def datetimeformat(value, format='%Y-%m-%d %H:%M:%S'):
    return value.strftime(format)

def render_template(template_name, **kwargs):
    env = Environment(
        loader=FileSystemLoader(searchpath='./templates')
    )
    env.filters['datetimeformat'] = datetimeformat

    template = env.get_template('{}.html'.format(template_name))
    html = template.render(**kwargs)

    with open('./htmlcov/{}.html'.format(template_name), encoding='utf-8', mode='w') as f:
        f.write(html)

    return html

def main():
    passed = []
    failed = []
    tafs = db.query(Taf).order_by(Taf.sent.desc()).all()
    for taf in tafs:
        parser = taf.parser()
        parser.validate()
        taf.html = parser.renderer('html')
        if taf.confirmed:
            if not parser.isValid() or parser.tips:
                taf.tips = parser.tips
                failed.append(taf)
            else:
                passed.append(taf)
    return render_template('index', passed=passed, failed=failed)


if __name__ == '__main__':
    output = main()