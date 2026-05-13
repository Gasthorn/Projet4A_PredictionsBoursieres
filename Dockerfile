FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ENV PORT=7860
ENV DEBUG=false

EXPOSE 7860

CMD ["python", "Interface Graphique/app.py"]