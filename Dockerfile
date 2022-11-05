FROM python:3.11

COPY main.sh /main.py
ENTRYPOINT ["./main.py"]
