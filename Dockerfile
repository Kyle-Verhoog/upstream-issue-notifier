FROM python:3.11

WORKDIR /src
COPY requirements.txt .
COPY main.py .
RUN python -m pip install -r requirements.txt
ENTRYPOINT ["/src/main.py"]
