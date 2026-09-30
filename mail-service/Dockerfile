FROM python:3.12-slim

ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /mail-service

# Зависимости
COPY requirements.txt /mail-service
RUN pip install --no-cache-dir -r requirements.txt
# Сам проект
COPY . /mail-service

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
