FROM mambaorg/micromamba:1.5.8

USER root
RUN apt-get update
RUN apt-get -y install nano git

COPY condarc /opt/conda/.condarc

RUN micromamba install --name base --channel conda-forge \
    python=3.11.9

RUN micromamba install --name base --channel maxiv-kits \
    tangods-isara2=4.1.0

CMD ["/opt/conda/bin/IsaraEmulator", "--enable-logging", "ISARA1", "10000", "1000"]
