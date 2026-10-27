FROM python:3.12-slim
WORKDIR /app
COPY core.py server.py configure.py ./
COPY agent/ ./agent/
COPY static/ ./static/
RUN useradd --create-home app && mkdir runtime && chown -R app:app /app
USER app
ENV HOST=0.0.0.0 PORT=8765 PYTHONUNBUFFERED=1
EXPOSE 8765
CMD ["python", "server.py"]
