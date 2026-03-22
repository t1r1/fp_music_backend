FROM python:3.14

RUN mkdir /app
WORKDIR /app

ADD requirements.txt /app/
RUN pip install -r requirements.txt

ADD api /app/api/

CMD [ "fastapi", "run", "api/main.py" ]