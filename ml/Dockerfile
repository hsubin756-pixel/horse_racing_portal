FROM python:3.12-slim
WORKDIR /app
COPY requirements.lock ./
RUN --mount=type=secret,id=ca_bundle pip install --no-cache-dir --cert /run/secrets/ca_bundle -r requirements.lock
COPY app.py train.py ./
RUN python train.py
USER 10001
EXPOSE 8000
CMD ["uvicorn","app:app","--host","0.0.0.0","--port","8000"]
