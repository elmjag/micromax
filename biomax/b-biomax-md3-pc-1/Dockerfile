FROM mambaorg/micromamba:1.4.2

USER root
RUN apt-get update
RUN apt-get -y install nano

RUN micromamba install --name base --channel conda-forge \
    python=3.10.12 \
    pytango=9.4.2 \
    circus=0.18.0

# used by md3video.py
RUN /opt/conda/bin/pip install simplejpeg==1.7.1

RUN mkdir /md3
COPY atcpserv.py exporter.py md3video.py sample.jpeg /md3/

COPY circus.conf /etc/
CMD [ "/opt/conda/bin/circusd", "/etc/circus.conf" ]
