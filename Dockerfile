FROM python:3.11-slim
WORKDIR /app
COPY requirements_kitchen_sink.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY . /app
ENV PYTHONUNBUFFERED=1
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s CMD python -c "print('ok')" || exit 1
CMD ["python","JARVIS_QAI_PRO.py"]
