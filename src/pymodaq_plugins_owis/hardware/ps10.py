"""Wrapper for OWIS PS 10 control units linked by a CANopen bus.

The master unit is connected by USB (virtual serial port), the slaves are reached through it by prefixing
each command with their two-digit slave ID.
"""
import time

import serial

BAUDRATE = 9600
TERMINATOR = b'\r'
COMMAND_DELAY = 0.05  # s, the manual asks for 20 to 40 ms between two commands


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