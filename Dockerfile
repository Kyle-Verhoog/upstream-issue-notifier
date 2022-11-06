FROM python:3.11

COPY main.py /main.py
ENTRYPOINT ["./main.py"]
