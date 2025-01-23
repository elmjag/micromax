#!/bin/sh

# stop circus managed mxcube and run new mxcube in this terminal
/opt/conda/bin/circusctl stop mxcube
cd /app/web && /opt/conda/bin/mxcubeweb-server --repository /app/conf/BioMAX --static-folder /opt/mxcube/build
