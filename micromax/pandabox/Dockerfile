FROM mambaorg/micromamba:1.5.8

USER root
RUN apt-get update
RUN apt-get -y install \
    git \
    # for troubleshooting
    nano

RUN micromamba install --name base --channel conda-forge \
    python=3.10.12 \
    circus=0.18.0

WORKDIR /

#
# install the PandABox emulator used by trigger generator tango device tests
#
RUN git clone https://gitlab.maxiv.lu.se/kits-maxiv/dev-micromax-panda.git app && \
    cd app && \
    git checkout 1.0.0

COPY circus.conf /etc/
CMD [ "/opt/conda/bin/circusd", "/etc/circus.conf" ]
