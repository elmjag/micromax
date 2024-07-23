FROM mambaorg/micromamba:1.5.8

USER root
RUN apt-get update
RUN apt-get -y install nano git

RUN micromamba install --name base --channel conda-forge \
    python=3.11.9 typing-extensions=4.10.0

RUN git clone https://gitlab.maxiv.lu.se/kits-maxiv/dev-maxiv-isara2.git /isara && \
    cd /isara && git checkout 2.0.0
COPY run.py /isara

WORKDIR /isara
CMD ["/isara/run.py"]
