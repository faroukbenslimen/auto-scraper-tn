FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app
EXPOSE 8502
ENV PYTHONUNBUFFERED=1
CMD ["streamlit", "run", "app.py", "--server.port=8502", "--server.headless=true"]
