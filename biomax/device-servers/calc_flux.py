from sardana.macroserver.macro import Macro, Type


class calculate_flux_mxcube(Macro):
    # Calculate flux at the sample position based on beam energy and Si pin photodiode readings downstream of sample
    # Based on interactive script /mxn/groups/biomax/wmxsoft/flux/fluxCalculator.py
    # Blame: AnaG

    param_def = [
        [
            "correct",
            Type.String,
            "1",
            "default 0 1: Attenuate the beam before measurement to avoid saturation.",
        ],
    ]
    result_def = [["flux", Type.Float, None, "flux"]]

    def run(self, correct):
        if correct == "1":
            current_meas = 0.002
        else:
            current_meas = 0.004

        return current_meas
