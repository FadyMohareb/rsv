FROM python:3.10-alpine

RUN pip install rq-dashboard==0.8.2.2

# https://github.com/rq/rq/issues/1469
RUN pip uninstall -y click
RUN pip install click==8.1.6

EXPOSE 9181

CMD ["rq-dashboard"]
