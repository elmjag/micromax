FROM mambaorg/micromamba:1.4.2

USER root
RUN apt-get update
RUN apt-get -y install nano

COPY condarc /opt/conda/.condarc

RUN micromamba install --name base --channel conda-forge \
    python=3.11.3 \
    circus=0.18.0

RUN micromamba install --name base --channel maxiv-kits \
    # pin numpy, as taurus (sardana's dependency)
    # does not work with numpy 2
    # https://gitlab.com/taurus-org/taurus/-/issues/1352
    numpy=1.26.4 \
    sardana=3.5.0post0+maxiv \
    tangods-mxdetectorcovers=1.0.1 \
    tangods-isara2=2.0.0 \
    tangods-micromax-panda=1.3.0

# install our circus 'plug-in'
RUN mkdir /opt/circus
COPY tango_ping.py /opt/circus/

COPY circus.conf /etc/

RUN mkdir /tangods
COPY albaem.py start_detc.py jungfrau.py eiger.py beam_shutter.py plc.py path_fixer.py /tangods/

RUN mkdir /sardana_ctrls
COPY faux.py /sardana_ctrls/

CMD [ "/opt/conda/bin/circusd", "/etc/circus.conf" ]
