FROM python:3.12-slim AS build
COPY .wheels /wheels
RUN pip install --no-cache-dir --prefix=/install --no-index --find-links=/wheels --require-hashes -r /wheels/requirements.hashed.txt
FROM python:3.12-slim
WORKDIR /app
COPY --from=build /install /usr/local
COPY app.py train.py evaluate.py ./
RUN python train.py && chmod -R a+rX /app
USER 10001
EXPOSE 8000
CMD ["uvicorn","app:app","--host","0.0.0.0","--port","8000"]
