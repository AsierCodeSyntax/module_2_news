FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    texlive-latex-base texlive-latex-recommended texlive-fonts-recommended \
    texlive-latex-extra latexmk \
    build-essential curl ca-certificates \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

CMD ["bash"]
