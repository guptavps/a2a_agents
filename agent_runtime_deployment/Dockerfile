FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY loan_closure_agent.py loan_closure_agent_card.py mcp_server.py ./

ENV LOAN_CLOSURE_AGENT_PORT=8080
EXPOSE 8080

CMD ["python", "loan_closure_agent.py"]
