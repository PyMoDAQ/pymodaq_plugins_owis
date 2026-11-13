from pymodaq.control_modules.move_utility_classes import (DAQ_Move_base, comon_parameters_fun,
                                                          main, DataActuatorType, DataActuator)
from pymodaq_utils.config import GlobalConfig
from pymodaq_utils.utils import ThreadCommand
from pymodaq_gui.parameter import Parameter
from qtpy import QtCore


from pymodaq_plugins_owis.hardware.ps10 import MockPS10Bus, PS10Axis, PS10Bus, PS10Error, slave_id_from_config

config = GlobalConfig()
AXES = config('owis', 'ps10', 'axes')


class DAQ_Move_OWIS_PS10(DAQ_Move_base):
    """Actuator plugin for OWIS positioning units driven by PS 10 control units.

    The docstring will be completed once the plugin is tested.
    """
    is_multiaxes = True
    _axis_names = [axis['name'] for axis in AXES]
    _controller_units = [axis['units'] for axis in AXES]
    _epsilons = 0.001  # mm or deg, about ten microsteps of the stages of the default configuration

    data_actuator_type = DataActuatorType.DataActuator

    params = [
        {'title': 'Port:', 'name': 'port', 'type': 'str', 'value': config('owis', 'ps10', 'port')},
    ] + comon_parameters_fun(axis_names=_axis_names)

    def ini_attributes(self):
        self.controller: PS10Bus | MockPS10Bus | None = None
        self.axis: PS10Axis | None = None
        self._home_timer = QtCore.QTimer()
        self._home_timer.setInterval(100)
        self._home_timer.timeout.connect(self._check_home)
        self._returning_home = False

    def ini_stage(self, controller=None):
        """Open the bus (master module) or reuse the one of the master, then switch the chosen axis on."""
        if self.is_master:
            port = self.settings['port']
            if port == 'MOCK':
                self.controller = MockPS10Bus(slave_ids=[slave_id_from_config(axis['slave_id']) for axis in AXES])
            else:
                self.controller = PS10Bus(port)
        else:
            self.controller = controller
        self._set_axis()
        state = self.axis.state()
        return f"{self.axis_name}: {AXES[self.axis_index_key]['stage']}, {state.name}", True

    def _set_axis(self):
        """Create the PS10Axis of the axis chosen in the settings and switch it on."""
        self.axis = PS10Axis.from_config(self.controller, AXES[self.axis_index_key])
        self.axis.init()

    def close(self):
        """Close the bus, only from the master module that opened it."""
        if self.is_master and self.controller is not None:
            self.controller.close()

    def get_actuator_value(self) -> DataActuator:
        """Position of the axis, read from the counter of its PS 10."""
        position = DataActuator(data=self.axis.get_position(), units=self.axis_unit)
        return self.get_position_with_scaling(position)

    def move_abs(self, value: DataActuator):
        """Start a move to the absolute target value; PyMoDAQ then polls the position."""
        value = self.check_bound(value)
        self.target_value = value
        value = self.set_position_with_scaling(value)
        self.axis.move_abs(value.value(self.axis_unit))

    def move_rel(self, value: DataActuator):
        """Start a move by value, as an absolute move to the current position plus value."""
        value = self.check_bound(self.current_value + value) - self.current_value
        self.target_value = value + self.current_value
        target = self.set_position_with_scaling(self.target_value)
        self.axis.move_abs(target.value(self.axis_unit))

    def move_home(self):
        """Reference run of the axis (REF1=4), then move to the home_position of the configuration.

        PyMoDAQ does not poll the position after move_home: _check_home calls move_done at the end.
        """
        self._returning_home = False
        self.axis.reference()
        self._home_timer.start()

    def _check_home(self):
        """Called every 100 ms during move_home: chain the reference run and the move to home_position."""
        if self.axis.is_moving():
            return
        if not self._returning_home:
            if not self.axis.is_referenced():
                self._home_timer.stop()
                self.emit_status(ThreadCommand('Update_Status',
                                               [f'reference run of {self.axis_name} failed: {self.axis.state().name}']))
                self.move_done()
                return
            home_position = AXES[self.axis_index_key].get('home_position', 0.)
            if home_position != 0.:
                self._returning_home = True
                self.axis.move_abs(home_position)
                return
        self._home_timer.stop()
        self.move_done()

    def stop_motion(self):
        """Stop the axis and tell PyMoDAQ that the move is over."""
        self._home_timer.stop()
        self.axis.stop()
        self.move_done()

    def commit_settings(self, param: Parameter):
        """Apply a change of the settings."""
        if param.name() == 'axis':
            self._set_axis()


if __name__ == '__main__':
    main(__file__)
