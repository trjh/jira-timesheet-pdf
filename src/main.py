import getpass
import textwrap
import argparse
import os
import socket
from flask import Flask, make_response, send_file, render_template
from collections import defaultdict
from datetime import datetime, timedelta
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter, inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table
from reportlab.lib.styles import getSampleStyleSheet
from jira import JIRA
from tabulate import tabulate

if 'JIRA_SERVER' in os.environ:
    server = os.environ['JIRA_SERVER']
else:
    server = input("Enter server (e.g. jira.example.com): ")

if 'JIRA_USER' in os.environ:
    username = os.environ['JIRA_USER']
else:
    username = input("Username (e.g. joe.doe): ")

if 'JIRA_USERPASSWORD' in os.environ:
    password = os.environ['JIRA_USERPASSWORD']
else:
    password = getpass.getpass("Password: ")

if 'JIRA_WORKLOG_FROM_DATE' in os.environ:
    from_date = datetime.strptime(os.environ['JIRA_WORKLOG_FROM_DATE'], '%Y-%m-%d').date()
else:
    from_date = datetime.strptime(input("From date (e.g. 2016-12-01): "), '%Y-%m-%d').date()

if 'JIRA_WORKLOG_TO_DATE' in os.environ:
    to_date = datetime.strptime(os.environ['JIRA_WORKLOG_TO_DATE'], '%Y-%m-%d').date()
else:
    to_date = datetime.strptime(input("To date (e.g. 2016-12-31): "),'%Y-%m-%d').date()

if 'JIRA_PROJECTID' in os.environ:
    project = os.environ['JIRA_PROJECTID']
else:
    project = input("JIRA Project ID: ")

parser = argparse.ArgumentParser()
parser.add_argument('--log', nargs='?', help='log')
args = parser.parse_args()

fastdebug = 0
html = 1

DATE_FORMAT = "%d/%m/%y"

app = Flask(__name__)

def get_worklog(assignee):

    if fastdebug != 1:
        jira = JIRA('https://{0}'.format(server),
                    basic_auth=(username, password))
        jql = 'timespent > 0 AND project = %s ORDER BY updated DESC' % project 
        issues = jira.search_issues(jql)
        
    assignees = dict()
    worklogs = []
    date_worklogs = defaultdict(list)
    issue_worklogs = defaultdict(list)
    issues_data = {}
    if fastdebug != 1:
        for issue in issues:
            issues_data[issue.key] = issue
            for w in jira.worklogs(issue.key):
                started = datetime.strptime(w.started[:-5],
                                            '%Y-%m-%dT%H:%M:%S.%f')
                # author = w.author
                # if author.name != assignee:
                #
                # this is probably crude and not very future-proofed, but it
                # works against my JIRA cloud instance, where the above does not
                author = w.raw['author']['name']
                assignees[author] =+ 1
                if author != assignee:
                    continue

                if not (from_date <= started.date() <= to_date):
                    continue

                spent = w.timeSpentSeconds / 3600

                worklog = {
                    "started": started, "spent": spent, "author": author,
                    "issue": issue,
                }
                worklogs.append(worklog)
                date_worklogs[started.date()].append(worklog)
                issue_worklogs[issue.key].append(worklog)

    ts = [
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONT', (0, 0), (-1, -1), 'DejaVuSans', 8, 8),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('FONT', (0, 0), (0, -1), 'DejaVuSans-Bold', 8, 8),
        ('FONT', (0, 0), (-1, 0), 'DejaVuSans-Bold', 8, 8),
    ]

    total_spent = 0.0

    day_spent = ['Total']       # key is a column number
    def cell_value(col, row, date, issue):
        nonlocal total_spent

        is_weekend = date.weekday() >= 5 if date else None
        if is_weekend:
            ts.append(('BACKGROUND', (col, 0), (col, -1), colors.whitesmoke))

        if row == 0 and date:
            return date.strftime("%d\n{0}".format(date.strftime("%a")[0]))
        if col == 0 and issue:
            return textwrap.fill("{0} - {1}".format(issue, issues_data[issue].fields.summary),50)
        if date and issue:
            task_total = sum(map(lambda w: w['spent'],
                                 filter(lambda w: w['issue'].key == issue,
                                        date_worklogs[date])))
            # this probably shouldn't be put here as it means it is computed a
            # lot more times than need be
            day_spent[col] += task_total
            total_spent += task_total
            return "{:.1f}".format(task_total) if task_total else ""
        return ""

    dates = get_dates_in_range(from_date, to_date)
    day_spent = ['Total'] + [0] * len(dates)
    print ("day_spent", day_spent)
    data = [
        [
            cell_value(col, row, date, issue)
            for col, date in enumerate([None] + dates)
        ]
        for row, issue in enumerate([None] + list(issue_worklogs.keys()))
    ]

    if fastdebug == 1:
        print(data)
        data = [['', '08\nM', '09\nT', '10\nW', '11\nT', '12\nF', '13\nS', '14\nS', '15\nM', '16\nT', '17\nW', '18\nT', '19\nF', '20\nS', '21\nS', '22\nM', '23\nT', '24\nW', '25\nT', '26\nF'], ['TICKET-1', '', '', '', '', '1.0', '', '', '', '', '', '', '', '', '', '', '', '', '', ''], ['TICKET-2', '', '', '', '', '', '', '', '0.2', '', '', '', '', '', '', '', '', '', '', ''], ['TICKET-3', '', '6.0', '', '', '6.0', '3.0', '2.0', '7.0', '', '', '', '', '', '', '', '', '', '', ''], ['TICKET-4', '', '', '', '8.0', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '']]
        day_spent = ['Total', 0, 6.0, 0, 8.0, 7.0, 3.0, 2.0, 7.166666666666667, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    day_spent = list(map(lambda x: round(x,1) if isinstance(x, float) else x, day_spent))
    #data.append('%.2f' % elem for elem in day_spent)
    #data.append((lambda x: '%.2f' % x if ininstance(x, float) else x) for elem in day_spent)
    #print(day_spent)
    data.append(day_spent)

    if html != 1:
        register_fonts()
        doc = SimpleDocTemplate('%s.pdf' % assignee, pagesize=landscape(letter))

        elements = []

        stylesheet = getSampleStyleSheet()
        p = Paragraph('''
        <para align=center spacea=30>
            <font size=15>Jira Tasks Report ({0}-{1})</font>
        </para>'''.format(
            from_date.strftime(DATE_FORMAT),
            to_date.strftime(DATE_FORMAT)), stylesheet["BodyText"])
        elements.append(p)

        cw = [None] + [0.2*inch] * (len(data[0]) - 1)
        t = Table(data, style=ts, colWidths=cw)
        elements.append(t)

        p = Paragraph('''
        <para align=center spaceb=15>
            <font size=10>Total Hours: {:.2f}</font>
        </para>'''.format(total_spent), stylesheet["BodyText"])
        elements.append(p)

        doc.build(elements)
        print('Done')
        return doc

    # now the html way...
    table = tabulate(data,headers="firstrow",tablefmt="html")
    return render_template('output.html',name=assignee,table=table,total=total_spent,assignees=assignees.keys())

def get_dates_in_range(from_date, to_date):
    dates = []
    current_date = from_date
    while True:
        dates.append(current_date)
        if current_date >= to_date:
            break
        current_date += timedelta(days=1)
    return dates


def register_fonts():
    pdfmetrics.registerFont(
        TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
               'UTF-8'))
    pdfmetrics.registerFont(
        TTFont('DejaVuSans-Bold',
               '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
               'UTF-8'))


@app.route("/worklog/<assignee>")
def worklog(assignee):
    if html == 1:
        return get_worklog(assignee)

    get_worklog(assignee)
    return send_file('../%s.pdf' % assignee)

@app.route("/worklog")
@app.route("/worklog/")
def worklogentry():
    return '''
<b>Hello, World!</b>
'''

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80)
