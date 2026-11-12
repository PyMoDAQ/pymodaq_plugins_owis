"""Tests of the OWIS PS 10 wrapper and plugin against the simulated bus (no hardware)."""
import pytest

from pymodaq.utils.data import DataActuator
from pymodaq.utils.plugin_testing import make_actuator, move_abs_and_wait, move_rel_and_wait
from pymodaq.utils.plugin_testing.harness import wait_for_signal

from pymodaq_plugins_owis.daq_move_plugins.daq_move_OWIS_PS10 import DAQ_Move_OWIS_PS10
from pymodaq_plugins_owis.hardware.ps10 import (AxisState, MockPS10Bus, PS10Axis, PS10Error,
                                                slave_id_from_config, steps_per_unit)


# wrapper

def test_steps_per_unit_of_the_stages():
    assert steps_per_unit(0.5, 1, 200, 50) == 20000   # HVM100N-30-HiSM
    assert steps_per_unit(1, 1, 200, 50) == 10000     # LTM60-25-HSM
    assert steps_per_unit(360, 180, 200, 50) == 5000  # DMT65-DM6-HSM


def test_slave_id_from_config():
    assert slave_id_from_config('master') is None
    assert slave_id_from_config(3) == 3


def test_absent_unit_raises():
    bus = MockPS10Bus(slave_ids=(None, 1))
    with pytest.raises(PS10Error):
        bus.query(5, '?ASTAT')


def test_axis_does_not_move_before_init():
    axis = PS10Axis(MockPS10Bus(slave_ids=(1,)), slave_id=1, steps_per_unit=10000)
    axis.move_abs(1.0)
    assert axis.state() == AxisState.DISABLED
    assert axis.get_position() == 0


# plugin

@pytest.fixture
def actuator(qapp):
    actuator = make_actuator(DAQ_Move_OWIS_PS10, port='MOCK')
    yield actuator
    actuator.close()


def test_init(actuator):
    assert actuator.initialized
    assert isinstance(actuator.controller, MockPS10Bus)


def test_move_abs(actuator):
    position = move_abs_and_wait(actuator, 0.5)
    assert position.value(actuator.axis_unit) == pytest.approx(0.5, abs=actuator.epsilon)


def test_move_rel(actuator):
    move_abs_and_wait(actuator, 0.5)
    position = move_rel_and_wait(actuator, 0.25)
    assert position.value(actuator.axis_unit) == pytest.approx(0.75, abs=actuator.epsilon)


def test_other_units_are_converted(actuator):
    if actuator.axis_unit != 'mm':
        pytest.skip('the first axis of the configuration is not in mm')
    position = move_abs_and_wait(actuator, DataActuator(data=500., units='um'))
    assert position.value('mm') == pytest.approx(0.5, abs=actuator.epsilon)


def test_stop_motion_ends_the_move(actuator):
    def start_and_stop():
        actuator.move_abs(DataActuator(data=20., units=actuator.axis_unit))
        actuator.stop_motion()

    wait_for_signal(actuator.move_done_signal, start_and_stop)
    assert actuator.get_actuator_value().value(actuator.axis_unit) < 20.


def test_slave_shares_the_bus_of_the_master(actuator):
    slave = make_actuator(DAQ_Move_OWIS_PS10, controller=actuator.controller)
    assert slave.initialized
    assert slave.controller is actuator.controller
    slave.close()
