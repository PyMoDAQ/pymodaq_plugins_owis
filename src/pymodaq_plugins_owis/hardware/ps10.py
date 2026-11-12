"""Wrapper for OWIS PS 10 control units linked by a CANopen bus.

The master unit is connected by USB (virtual serial port), the slaves are reached through it by prefixing
each command with their two-digit slave ID.
"""
import time
from enum import Enum

import serial

BAUDRATE = 9600
TERMINATOR = b'\r'
COMMAND_DELAY = 0.05  # s, the manual asks for 20 to 40 ms between two commands
MASTER = 'master'  # slave_id of the unit connected by USB in the configuration

class PS10Error(Exception):
    """Raised when a PS 10 unit does not answer a query."""


class PS10Bus:
    """Serial link to the master PS 10 and, through it, to its slaves.

    A unit is addressed by its slave ID: None for the master, 1, 2, 3... for the slaves.
    """

    def __init__(self, port: str, baudrate: int = BAUDRATE, timeout: float = 0.5):
        self._serial = serial.Serial(port, baudrate, timeout=timeout)

    @staticmethod
    def _prefix(slave_id) -> str:
        return '' if slave_id is None else f'{slave_id:02d}'

    def write(self, slave_id, command: str):
        """Send a command that has no reply (INIT1, PGO1...)."""
        self._serial.reset_input_buffer()
        self._serial.write((self._prefix(slave_id) + command).encode('ascii') + TERMINATOR)
        time.sleep(COMMAND_DELAY)

    def query(self, slave_id, command: str) -> str:
        """Send a query (?CNT1, ?ASTAT...) and return its reply without the terminator."""
        self.write(slave_id, command)
        reply = self._serial.read_until(TERMINATOR)
        if not reply.endswith(TERMINATOR):
            unit = 'master' if slave_id is None else f'slave {slave_id}'
            raise PS10Error(f'no reply from the {unit} to {command}')
        return reply[:-len(TERMINATOR)].decode('ascii')

    def close(self):
        if self._serial.is_open:
            self._serial.close()


class AxisState(str, Enum):
    """States returned by ?ASTAT (PS 10 manual, command set)."""
    NOT_INITIALIZED = 'I'
    DISABLED = 'O'
    READY = 'R'
    POSITIONING = 'T'
    VELOCITY_MODE = 'V'
    REFERENCE_RUN = 'P'
    RELEASING_LIMIT_SWITCH = 'F'
    STOPPED_AT_LIMIT_SWITCH = 'L'
    STOPPED_AT_BRAKE_SWITCH = 'B'
    LIMIT_SWITCH_ERROR = 'A'
    MOTION_CONTROLLER_ERROR = 'M'
    TIMEOUT = 'Z'
    PHASE_INITIALIZATION = 'H'
    NOT_ENABLED = 'U'
    MOTION_ERROR = 'E'


MOVING_STATES = (AxisState.POSITIONING, AxisState.VELOCITY_MODE,
                 AxisState.REFERENCE_RUN, AxisState.RELEASING_LIMIT_SWITCH)

def steps_per_unit(pitch: float, gear_ratio: float, fullsteps_per_revolution: int, microsteps: int) -> float:
    """Microsteps per mm (or per degree) of a stage driven by a stepper motor.

    The values are those shown by OWISoft in Control > Define positioning unit.
    """
    return gear_ratio * fullsteps_per_revolution * microsteps / pitch


class PS10Axis:
    """The single axis of one PS 10 unit, in physical units (mm or deg).

    Parameters
    ----------
    bus: PS10Bus
        the serial link shared by all the units
    slave_id: int or None
        None for the master, the slave ID otherwise
    steps_per_unit: float
        microsteps per mm (linear stage) or per degree (rotation stage)
    """

    def __init__(self, bus: PS10Bus, slave_id, steps_per_unit: float):
        self._bus = bus
        self.slave_id = slave_id
        self.steps_per_unit = steps_per_unit

    @classmethod
    def from_config(cls, bus: PS10Bus, axis: dict) -> 'PS10Axis':
        """Build an axis from one [[ps10.axes]] block of the configuration."""
        slave_id = None if axis['slave_id'] == MASTER else int(axis['slave_id'])
        return cls(bus, slave_id, steps_per_unit(axis['pitch'], axis['gear_ratio'],
                                                 axis['fullsteps_per_revolution'], axis['microsteps']))

    def init(self):
        """Switch the axis on and use absolute targets."""
        self._bus.write(self.slave_id, 'INIT1')
        self._bus.write(self.slave_id, 'ABSOL1')

    def state(self) -> AxisState:
        """Current state of the axis, see AxisState."""
        reply = self._bus.query(self.slave_id, '?ASTAT')
        try:
            return AxisState(reply)
        except ValueError:
            raise PS10Error(f'unknown axis state {reply!r}') from None

    def is_moving(self) -> bool:
        return self.state() in MOVING_STATES

    def get_position(self) -> float:
        return int(self._bus.query(self.slave_id, '?CNT1')) / self.steps_per_unit

    def move_abs(self, position: float):
        """Start a move to position; return without waiting for the end of the move."""
        steps = round(position * self.steps_per_unit)
        self._bus.write(self.slave_id, f'PSET1={steps}')
        self._bus.write(self.slave_id, 'PGO1')

    def stop(self):
        self._bus.write(self.slave_id, 'STOP1')
