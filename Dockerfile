FROM python:3.11-slim
WORKDIR /atelier

COPY ./requirements.txt /atelier/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /atelier/requirements.txt

COPY ./packages/discussant /atelier/discussant

CMD ["python3", "-m", "discussant.main"]
