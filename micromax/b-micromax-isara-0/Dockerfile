FROM mambaorg/micromamba:1.5.8

USER root
RUN apt-get update
RUN apt-get -y install nano git

COPY condarc /opt/conda/.condarc

RUN micromamba install --name base --channel conda-forge \
    python=3.11.9

RUN micromamba install --name base --channel maxiv-kits \
    tangods-isara2=4.2.2

CMD ["/opt/conda/bin/IsaraEmulator", "--enable-logging", "ISARA2", "10000", "1000"]
