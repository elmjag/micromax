FROM docker.io/mambaorg/micromamba:2.3.2

USER root
RUN apt-get update
RUN apt-get -y install \
    git \
    # for troubleshooting
    nano

COPY condarc /opt/conda/.condarc

RUN micromamba install --name base --channel maxiv-kits \
    python=3.11.9 \
    tangods-micromax-panda=1.4.0

CMD [ "/opt/conda/bin/micromax-pandabox-emulator" ]
