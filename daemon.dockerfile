FROM python:3

RUN mkdir -p /opt/src/applications/daemon
WORKDIR /opt/src/applications

COPY applications/daemon/application.py ./daemon/application.py
COPY applications/configuration.py ./configuration.py
COPY applications/manage.py ./manage.py
COPY applications/models.py ./models.py
COPY applications/roleDecorator.py ./roleDecorator.py
COPY applications/requirements.txt ./requirements.txt

RUN pip install -r ./requirements.txt

ENV PYTHONPATH="/opt/src"

ENTRYPOINT ["python", "./daemon/application.py"]
