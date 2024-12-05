#!/bin/sh

# stop circus managed mxcube and run new mxcube in this terminal
circusctl stop mxcube
/app/web/mxcubeweb-server --repository /app/conf/MicroMAX --static-folder /opt/mxcube/build
