FROM mambaorg/micromamba:1.4.2

USER root
RUN apt-get update
RUN apt-get -y install \
    # need for lucid3
    libgl1-mesa-glx \
    iputils-ping git nano

USER $MAMBA_USER

COPY condarc /opt/conda/.condarc

RUN micromamba install --name base --channel conda-forge \
    python=3.9.16 \
    pytango=9.4.1 \
    itango=0.1.9 \
    redis-server=7.0.11 \
    circus=0.18.0 \
    # install as conda package, so pip does not try to compile it
    python-ldap=3.4.0 \
    # for building front-end \
    nodejs=18.15.0 \
    # MAXIV specific packages for MXCube
    sdm=1.8.8 \
    sardana=3.4.0

#
# copy mxcube repositories
#

WORKDIR /app

COPY --chown="${MAMBA_USER}:${MAMBA_USER}" mxcubecore core
COPY --chown="${MAMBA_USER}:${MAMBA_USER}" mxcube3 web
COPY --chown="${MAMBA_USER}:${MAMBA_USER}" cfg-maxiv-mxcubecore conf

# remove 'mxcubecore' and 'mxcube_video_streamer' packages from dependencies
RUN sed -i '/^mxcubecore\|^mxcube_video_streamer/d' web/pyproject.toml
RUN /opt/conda/bin/pip install -e web
RUN /opt/conda/bin/pip install -e core

# build front-end
WORKDIR /app/web/ui
RUN /bin/micromamba run -p /opt/conda npm clean-install
RUN /bin/micromamba run -p /opt/conda npm run build

# install our circus 'plug-in'
COPY tango_ping.py /opt/circus/

COPY circus.conf /etc/

WORKDIR /app
CMD [ "/opt/conda/bin/circusd", "/etc/circus.conf" ]
