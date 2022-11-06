FROM python:3.10

WORKDIR /src
COPY requirements.txt .
COPY main.py .
RUN python -m pip install -r requirements.txt
ENTRYPOINT ["/src/main.py"]
