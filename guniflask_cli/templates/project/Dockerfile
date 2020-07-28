FROM python:3.7

ADD ./ /opt/{{project_name}}
WORKDIR /opt/{{project_name}}

RUN chmod +x bin/manage \
  && pip install -r requirements/app.txt

CMD bin/manage start --daemon-off
