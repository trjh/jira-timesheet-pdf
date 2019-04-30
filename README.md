# Jira Timesheet Export

One of the trivial tasks in Jira without buying an additional plugin is the
export of a timesheet for particular user. The purpose of this script is to
allow you to export the timesheet for specific user time range, only using the
default Jira API.

I forked the [original](jordanjambazov/jira-timesheet-pdf) because I wanted
the simpler view of the table in HTML, and to be able to see at a glace which
days I'd logged 7 or more hours on.

# How to run the script?

- Clone this repository
- `docker build -t jira-timesheet-stage stage`
- `docker build -t jira-timesheet-export .`
- (Optional) Set ENV data using `env` file (copy env.default to env and adapt variables)
- ```docker run --env-file=env -it -p 8080:80 -v `pwd`:/code jira-timesheet-export python3 src/main.py ```
- Provide input once required
- Browse to http://localhost:8080/worklog/`<assignee>` where `<assignee>` is the name of the Jira worklog author you are interested in reporting on
