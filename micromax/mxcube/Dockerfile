FROM docker.io/mambaorg/micromamba:2.3.2

USER root
RUN apt-get update
RUN apt-get -y install \
    # to do the needful
    git \
    # for troubleshooting
    procps tree iputils-ping nano

COPY activedirectory.yml /etc/sdm/

# install kafka certificates for SciCat
COPY ca.crt user.crt user.key /etc/ssl/certs/kafka/

COPY condarc /opt/conda/.condarc
RUN micromamba install --name base --channel conda-forge \
    python=3.11.10 \
    pytango=9.4.1 \
    itango=0.1.9 \
    redis-server=7.0.11 \
    circus=0.18.0 \
    # for video streamer
    ffmpeg \
    # install as conda package, so pip does not try to compile it
    python-ldap=3.4.3 \
    # for building front-end \
    nodejs=20.12.2 \
    pnpm=9.1.1 \
    # MAXIV specific packages for MXCube
    pandablocks=0.10.3 \
    sdm=1.8.10 \
    sardana=3.5.0post0+maxiv \
    scifish=1.3.2

#
# install MicroMAX Dashboard
#

RUN micromamba create --name dashboard
RUN micromamba install --name dashboard app-micromax-dashboard=0.12.0

# add emulator specific dashboard configuration
COPY dboard_config.py /opt/dashboard/config.py

#
# Patch a bit config files.
#
# Remove web proxy from ISPyB configuration, to avoid emulating web proxy.
# ISPyB is accessible without proxy on white network.
#
# Disable uploads to SciCat, avoid uploading data when running in the emulator.
#
RUN cd /opt/conda/envs/dashboard/lib/python3.11/site-packages/dboard/static/micromax-templates && \
    sed -i '/proxy_address/d' lims.yaml && \
    sed -i 's/scicat_enabled: true/scicat_enabled: false/' collect.yaml-template

# generate initial MXCuBE configuration files
RUN /opt/conda/envs/dashboard/bin/write_mxcube_config

#
# clone mxcube repositories
#

WORKDIR /app

# clone 'core' repository on maxiv-develop branch
RUN git clone --depth 8 --branch maxiv-develop https://gitlab.maxiv.lu.se/kits-maxiv/mxcube/mxcubecore.git core

# clone 'web' repository on maxiv-develop branch
RUN git clone --depth 8 --branch maxiv-develop https://gitlab.maxiv.lu.se/kits-maxiv/mxcube/mxcube3.git web

RUN /opt/conda/bin/pip install -e core[maxiv]
RUN /opt/conda/bin/pip install -e web

# build front-end
WORKDIR /app/web/ui
RUN /bin/micromamba run -p /opt/conda pnpm install
RUN /bin/micromamba run -p /opt/conda pnpm run build

# move generated UI files outside of git repository,
# this way we can mount over /app/web directory
# from outside, if needed, for editing purpuses
RUN mkdir /opt/mxcube
RUN mv /app/web/ui/build /opt/mxcube

#
# space group look-up file
#
RUN mkdir -p /mxn/groups/sw/mxsw/mxcube_scripts/
COPY spg_pro_xtal_tab.txt /mxn/groups/sw/mxsw/mxcube_scripts/

#
# install crystfel template files
#
RUN mkdir -p /mxn/groups/sw/mxsw/mxcube_scripts/template/
COPY jungfrau_geom_temp.txt crystfel_index_temp.txt /mxn/groups/sw/mxsw/mxcube_scripts/template/

#
# install pandabox schema files
#
RUN mkdir -p /data/staff/micromax/software/configs/pandabox_eh1/
COPY pandabox/* /data/staff/micromax/software/configs/pandabox_eh1/

#
# Set-up micromax-service user,
# which is used for running MXCuBE at the beamline.
#
# NOTE: for now, the MXCuBE is run as 'root' user
# in the emulator.
#
RUN addgroup micromax
RUN adduser --system --no-create-home --ingroup micromax micromax-service

#
# Add a couple of proposal user groups.
# This is needed to emulate creation of proposal directories in
# /data/visitors/micromax folder.
#

# the 'Test mxCuBe' proposal user group
RUN addgroup --allow-bad-names 20230002-group
# the 'TEST for checking data handling' proposal user group
RUN addgroup --allow-bad-names 20170251-group

#
# Create /data/visitors/micromax folder.
#
RUN mkdir --parents --mode=g+s /data/visitors/micromax
RUN chown micromax-service:micromax /data/visitors/micromax

#
# install convenience scripts for running MXCuBE from terminal
# run.sh   - runs the python backend (mxcubeweb-server)
# start.sh - starts the front-end in developer mode
#
COPY run.sh start.sh /app/

# MD3 front and back lights toggler script
COPY md3_light.py /app/

# install our circus 'plug-in'
RUN mkdir /opt/circus
COPY tango_ping.py /opt/circus/

COPY circus.conf /etc/

#
# allows us to run git commands when these folder
# are bound to host folders in docker-compose.yml
#
RUN git config --global --add safe.directory /app/dboard
RUN git config --global --add safe.directory /app/web
RUN git config --global --add safe.directory /app/core

WORKDIR /app
CMD [ "/opt/conda/bin/circusd", "/etc/circus.conf" ]
