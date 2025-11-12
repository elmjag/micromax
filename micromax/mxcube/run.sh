#!/bin/sh

# stop circus managed mxcube and run new mxcube in this terminal
circusctl stop mxcube
mxcubeweb-server --repository /app/conf --static-folder /opt/mxcube/build
