FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py ./

ENV LOAN_CLOSURE_AGENT_PORT=8090
EXPOSE 8090

CMD ["python", "loan_closure_a2a_server.py"]