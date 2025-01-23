FROM mambaorg/micromamba:1.4.2

USER root
RUN apt-get update
RUN apt-get -y install supervisor nano
COPY supervisord.conf /etc/supervisor/supervisord.conf

RUN micromamba install --name base --channel conda-forge python=3.11.3 pytango=9.4.1

COPY machinestatus.py dcct.py id_gap.py /

CMD [ "/usr/bin/supervisord", "--nodaemon", "--configuration", "/etc/supervisor/supervisord.conf" ]
