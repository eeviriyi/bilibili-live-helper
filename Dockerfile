FROM python:3.10-alpine

ENV TZ=Asia/Shanghai

WORKDIR /app/fansMedalHelper

COPY requirements.txt ./

RUN apk add --no-cache tzdata \
    && pip install --no-cache-dir -r requirements.txt

COPY . ./

CMD ["python3", "-m", "fans_medal_helper"]
