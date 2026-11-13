pymodaq_plugins_owis
####################

.. image:: https://img.shields.io/pypi/v/pymodaq_plugins_owis.svg
   :target: https://pypi.org/project/pymodaq_plugins_owis/
   :alt: Latest Version

.. image:: https://readthedocs.org/projects/pymodaq/badge/?version=latest
   :target: https://pymodaq.readthedocs.io/en/stable/?badge=latest
   :alt: Documentation Status

.. image:: https://github.com/jerlfan/pymodaq_plugins_owis/actions/workflows/Test.yml/badge.svg
    :target: https://github.com/jerlfan/pymodaq_plugins_owis/actions/workflows/Test.yml


PyMoDAQ plugin for OWIS positioning units driven by PS 10 control units, chained on their CANopen bus.

This branch targets **PyMoDAQ 5.3.x** (Python 3.10 to 3.13).

Authors
=======

* Jérémie Margueritat (jeremie.margueritat@univ-lyon1.fr)

Instruments
===========

Below is the list of instruments included in this plugin

Actuators
+++++++++

* **OWIS_PS10**: OWIS stages driven by PS 10 control units, one axis per unit, the units being chained on their
  CANopen bus (tested with HVM100N-30-HiSM, LTM60-25-HSM and DMT65-DM6-HSM stages)


Installation instructions
=========================

* Tested with PyMoDAQ 5.3.10, Python 3.12, Windows 11.
* Install the USB driver of the PS 10, supplied by OWIS with OWISoft.
* Configure each stage once with OWISoft (currents, limit and reference switches, reference velocities): the plugin
  uses the parameters stored in the units. Close OWISoft before using the plugin, both use the same serial port.


Configuration
=============

The serial port and the axes are read from the configuration of the plugin. Describe your setup in your local
configuration file (``config_owis.toml`` in the ``config`` folder of your PyMoDAQ user directory), with
PyMoDAQ closed, since PyMoDAQ rewrites this file when it closes. Each ``[[ps10.axes]]`` block describes one unit,
with the values shown by OWISoft in *Control > Define positioning unit*::

    [ps10]
    port = 'COM8'  # MOCK to simulate the units

    [[ps10.axes]]
    name = 'X'
    stage = 'LTM60-25-HSM'
    slave_id = 'master'  # else the slave ID of the unit on the CANopen bus
    units = 'mm'  # 'degree' for a rotation stage
    pitch = 1.0
    gear_ratio = 1.0
    fullsteps_per_revolution = 200
    microsteps = 50
    home_position = 12.5  # position reached after the reference run

The axes of the local file replace those of the template. *Home* runs the reference run of the PS 10 (mode 4:
approach the reference switch, release it, set the position to 0), then moves the axis to its ``home_position``.


Development
===========

* Install your plugin in editable mode: ``pip install -e .``
* Check it, without any hardware: ``check_plugin`` and ``pytest tests``
* If you use an AI coding assistant, point it to ``AGENTS.md``: it describes the patterns to follow for instrument
  plugins, Dashboard extensions (``CustomExt``, whenever instruments are involved) and standalone apps
  (``CustomApp``, only if no instruments are needed).