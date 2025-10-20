FROM docker.io/mambaorg/micromamba:2.3.2

USER root
RUN apt-get update
RUN apt-get -y install nano git

COPY condarc /opt/conda/.condarc

RUN micromamba install --name base --channel conda-forge \
    python=3.11.9

RUN micromamba install --name base --channel maxiv-kits \
    tangods-isara2=4.4.0

# config file for emulator
RUN mkdir --parents /opt/isara
COPY config.toml /opt/isara

CMD ["/opt/conda/bin/IsaraEmulator", "--enable-logging", "/opt/isara/config.toml"]
