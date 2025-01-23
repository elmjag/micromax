# BioMAX and MicroMAX emulation

A series of docker images that emulate BioMAX and MicroMAX beamlines.
The aim of the emulation is to be able to run MxCube, as it's deployed at the beamlines, inside one of the containers.

## Building

To build all required images for BioMAX run:

    docker compose --file biomax.yaml build

To build all required images for MicroMAX run:

    docker compose --file micromax.yaml build

Note that you need to be on MAXIV white network, when building images.
The images are cloning code from MAXIV internal repositories.

## Running

Start BioMAX emulation with:

    docker compose --file biomax.yaml up

Start MicroMAX emulation with:

    docker compose --file micromax.yaml up

Note that you need to be on MAXIV white network, when running emulation.
The MXCuBE need to access ISPyB API.

## Images

### Common Images

`tango-cs`

The 'tango host' of the beamline tango devices.

`csproxy-tango-db`

Hosts green network tango database.

`g-v-csproxy-0`

The 'tango host' of proxied green network tango devices.

`common/csproxy-ds`

Runs emulated proxied green network tango devices.

### BioMAX Images

`biomax/tango-db`

Hosts the BioMAX tango database.

`biomax/device-servers`

Runs the emulated BioMAX tango device servers.
Runs the Sardana Pool and MacroServers with emulated BioMAX elements.

`biomax/mxcube`

Runs the MicroMAX version of the MxCube.

`biomax/b-biomax-md3-pc-1`

Runs the BioMAX MD3 diffractometer emulator.

`biomax/dbg`

Can be used for debugging and troubleshooting BioMAX instance.

### MicroMAX Images

`micromax/tango-db`

Hosts the MicroMAX tango database.

`micromax/device-servers`

Runs the emulated MicroMAX tango device servers.
Runs the Sardana Pool and MacroServers with emulated MicroMAX elements.

`micromax/mxcube`

Runs the MicroMAX version of the MxCube.

`micromax/b-micromax-md3-pc`

Runs the MicroMAX MD3Up diffractometer emulator.

`micromax/b-micromax-isara-0`

Runs ISARA2 socket API emulator.

`micromax/pandabox`

Runs the PandABox API emulator.

`micromax/dbg`

Can be used for debugging and troubleshooting MicroMAX instance.
