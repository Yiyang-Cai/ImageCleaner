#Version: 0.0.1
FROM python:2

ENV VIRTUAL_MANAGER_PASS_WORD="6CbYoS28" VIRTUAL_MANAGER_USER_NAME="svc_p_itools_ecs"

WORKDIR /usr/src/app

ADD . /usr/src/app/

RUN pip install --no-cache-dir requests
