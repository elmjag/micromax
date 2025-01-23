FROM mambaorg/micromamba:1.4.2

USER root
RUN apt-get update
RUN apt-get -y install supervisor nano netcat

COPY condarc /opt/conda/.condarc
RUN micromamba install --name base --channel conda-forge \
    python=3.9.16 \
    pytango=9.4.1 \
    itango=0.1.9 \
    # make 'spock' available
    sardana=3.5.0post0+maxiv

RUN mkdir -p /root/.ipython/profile_spockdoor
COPY ipython_config.py /root/.ipython/profile_spockdoor/

COPY spin.py /

CMD [ "/spin.py" ]
