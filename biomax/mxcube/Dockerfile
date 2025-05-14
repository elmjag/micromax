FROM mambaorg/micromamba:2.1.1

USER root
RUN apt-get update
RUN apt-get -y install \
    # need for lucid3
    libgl1-mesa-glx \
    # to do the needful
    git \
    # for troubleshooting
    procps tree iputils-ping nano netcat-openbsd

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
    sdm=1.8.10 \
    sardana=3.5.0post0+maxiv \
    scifish=1.3.2

#
# clone mxcube repositories
#

WORKDIR /app

# clone 'configuration' repository on master branch
RUN git clone --depth 8 --branch master https://gitlab.maxiv.lu.se/kits-maxiv/mxcube/cfg-maxiv-mxcubecore.git conf

# clone 'core' repository on maxiv-develop branch
RUN git clone --depth 8 --branch maxiv-develop https://gitlab.maxiv.lu.se/kits-maxiv/mxcube/mxcubecore.git core

# clone 'web' repository on maxiv-develop branch
RUN git clone --depth 8 --branch maxiv-develop https://gitlab.maxiv.lu.se/kits-maxiv/mxcube/mxcube3.git web

# remove web proxy from ISPyB configuration, to avoid emulating web proxy.
# ISPyB is accessible without proxy on white network.
COPY no_lims_proxy.patch /tmp
RUN cd conf && git apply /tmp/no_lims_proxy.patch

RUN /opt/conda/bin/pip install -e web
RUN /opt/conda/bin/pip install -e core[maxiv]

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
COPY crystfel_index_temp.txt /mxn/groups/sw/mxsw/mxcube_scripts/template/

#
# install data files used by misc scan types
#
RUN mkdir -p /mxn/groups/biomax/amptek/maxlab_macros/
WORKDIR /mxn/groups/biomax/amptek/maxlab_macros

# some kind of data file for loaded by BIOMAXXRFSpectrum hardware object
COPY energy_edges.dat .
# some kind of data file for loaded by BIOMAXContinuousScan hardware object
COPY remote-energy.dat .

#
# install convenience scripts for running MXCuBE from terminal
# run.sh   - runs the python backend (mxcubeweb-server)
# start.sh - starts the front-end in developer mode
#
COPY run.sh start.sh /app/

# install our circus 'plug-in'
RUN mkdir /opt/circus
COPY tango_ping.py /opt/circus/

COPY circus.conf /etc/

#
# allows us to run git commands when these folder
# are bound to host folders in docker-compose.yml
#
RUN git config --global --add safe.directory /app/conf
RUN git config --global --add safe.directory /app/web
RUN git config --global --add safe.directory /app/core

WORKDIR /app
CMD [ "/opt/conda/bin/circusd", "/etc/circus.conf" ]
