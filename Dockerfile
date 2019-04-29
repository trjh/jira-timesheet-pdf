FROM jira-timesheet-stage
WORKDIR /code
ADD requirements.txt /code/requirements.txt
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8
RUN pip install -r requirements.txt
ADD . /code
