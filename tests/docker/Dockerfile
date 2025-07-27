FROM python:3.12-slim
WORKDIR /app
COPY sigil /app/sigil
COPY appdirs /app/appdirs
COPY tests /app/tests
COPY pyproject.toml /app/
RUN pip install -e .[secrets] pytest
CMD []
