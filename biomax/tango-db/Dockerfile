FROM registry.gitlab.com/tango-controls/docker/mysql:5

# set-up our MicroMAX specific tango devices, sardana etc
COPY z_biomax_tango.sql /docker-entrypoint-initdb.d/
