FROM mambaorg/micromamba:1.5.8

USER root
RUN apt-get update
RUN apt-get -y install nano git

COPY condarc /opt/conda/.condarc
COPY isara_config.toml /conf/isara_config.toml

RUN micromamba install --name base --channel conda-forge \
    python=3.11.9

RUN micromamba install --name base --channel maxiv-kits \
    tangods-isara2==4.2.3

CMD ["/opt/conda/bin/IsaraEmulator", "--enable-logging", "/conf/isara_config.toml"]
