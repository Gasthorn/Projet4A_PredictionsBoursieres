FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libopenblas-dev \
    liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install dlib-bin
RUN pip install --no-deps face_recognition
RUN pip install -r requirements.txt --ignore-requires-python

COPY . .

ENV PORT=7860
ENV DEBUG=false

EXPOSE 7860

CMD ["python", "Interface Graphique/app.py"]