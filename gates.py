import warnings
from threading import Timer

# CONSTANTS
MINUS = -1
NEUTRAL = 0
PLUS = 1

VALID_STATES = {MINUS, NEUTRAL, PLUS}
STATE_NAME = {
  PLUS: '(+)',
  MINUS: '(-)',
  NEUTRAL: '(0)',
}

DELAY_ENABLED = False

class BadStateException(Exception):
  def __init__(self, badState):
    super().__init__('Cannot set state to: ' + str(badState))

class ConnectionError(ValueError):
  pass


class ConnectionPoint:
  READER = MINUS
  WRITER = PLUS
  HIGH_IMPEDANCE = NEUTRAL
  def __init__(self, io=False, controller=False, state=False):
    """
    Args:
      io: The state to be in. PLUS is writer, MINUS is reader, and NEUTRAL is
        high impedence (neither read nor write)
      state: The initial state.
    """
    self._io = io or ConnectionPoint.HIGH_IMPEDANCE
    self._state = state or NEUTRAL
    self._controller = controller
    self._wire = False

  def HasWire(self):
    return bool(self._wire)

  def Connect(self, wire):
    if self.HasWire():
      raise ConnectionError('%s already connected' % wire)
    self._wire = wire

  def Disconnect(self):
    if not self.HasWire():
      warnings.warn('No wire to disconnect')
      return
    res = self._wire
    self._wire = False
    return res

  def IsWriter(self):
    return self._io is ConnectionPoint.WRITER

  def IsReader(self):
    return self._io is ConnectionPoint.READER

  def GetState(self):
    return self._state

  def State(self):
    return STATE_NAME[self._state]

  def SetStateWire(self, state):
    if self.IsReader():
      self._state = state
      if (self._controller):
        self._controller.Update()
    else:
      warning.warn('Attempting to set the state of a write/high impedance')

  def SetStateWrite(self, state):
    if not self.IsReader():
      self._state = state
      if self.HasWire():
        self._wire.Update()
    else:
      warnings.warn('Attempting to SetStateWrite on a non-reading connection point')

  def __str__(self):
    io = self.IsReader() and 'Reader' or self.IsWriter() and 'Writer' or 'High impedance'
    return 'ConnectionPoint<%s,%s>' % (io, self.State())

class Wire:
  """Connection point of everything. """
  def __init__(self):
    self._connections = []

  def Update(self):
    write_states = [c.GetState() for c in self._connections if c.IsWriter()]
    # No readers
    if not write_states:
      return

    if len(write_states) > 2:
      warnings.warn('More than one writer on this wire, defaulting to first found value')

    write_state = write_states[0]
    for connection in self._connections:
      if connection.IsReader():
        connection.SetStateWire(write_state)

  # TODO: Consider doing checks here so that connections are determined
  # beforehand. This way we can disconnect or reconnect things as necessary.
  def Connect(self, connectable):
    if connectable in self._connections:
      raise ConnectionError('%s is already connected' % connectable)
    self._connections.append(connectable)
    connectable.Connect(self)

  def Disconnect(self, connectable):
    if connectable not in self._connections:
      raise ConnectionError('%s is not connected' % connectable)
    self._connections.pop(self._connections.index(connectable))
    connectable.Disconnect()

  def DisconnectAll(self):
    for connection in self._connections:
      connection.Disconnect()
    self._connections.clear()

  def __str__(self):
    return 'Wire<%d conns>' % len(self._connections)


class GateMonadic:
  def __init__(self):
    self._input = ConnectionPoint(ConnectionPoint.READER, self)
    self._output = ConnectionPoint(ConnectionPoint.WRITER, self)
    self._delay = 0

  def SetInputWire(self, wire):
    wire.Connect(self._input)

  def SetOutputWire(self, wire):
    wire.Connect(self._output)

  def SetOutputState(self, state):
    # Output is already at the current state, no need to do anything.
    if self._output.GetState() == state: return

    if DELAY_ENABLED:
      Timer(self._delay, lambda: self._output.SetStateWrite(state))
    else:
      self._output.SetStateWrite(state)

  def Update(self):
    raise NotImplementedError('Update not implemented for %s' % type(self).__name__)

  def __str__(self):
    return '%s<I: %s, O: %s>' % \
        (type(self).__name__, self._input.State(), self._output.State())

class GateIdentity(GateMonadic):
  def Update(self):
    val = self._input.GetState()
    self.SetOutputState(val)

class GateIncrement(GateMonadic):
  """
  in  | out
  (-) | (0)
  (0) | (+)
  (+) | (-)
  """
  LOGIC_MAP = {
    PLUS: MINUS,
    NEUTRAL: PLUS,
    MINUS: NEUTRAL,
  }
  def Update(self):
    in_state = self._input.GetState()
    self.SetOutputState(GateIncrement.LOGIC_MAP[in_state])

class GateDecrement(GateMonadic):
  """
  in  | out
  (-) | (+)
  (0) | (-)
  (+) | (0)
  """
  LOGIC_MAP = {
    PLUS: NEUTRAL,
    NEUTRAL: MINUS,
    MINUS: PLUS,
  }
  def Update(self):
    in_state = self._input.GetState()
    self.SetOutputState(GateDecrement.LOGIC_MAP[in_state])

class GateNegate(GateMonadic):
  """
  in  | out
  (-) | (+)
  (0) | (0)
  (+) | (-)
  """
  LOGIC_MAP = {
    PLUS: MINUS,
    NEUTRAL: NEUTRAL,
    MINUS: PLUS,
  }
  def Update(self):
    in_state = self._input.GetState()
    self.SetOutputState(GateNegate.LOGIC_MAP[in_state])

class GateIsHigh(GateMonadic):
  """
  in  | out
  (-) | (-)
  (0) | (-)
  (+) | (+)
  """
  LOGIC_MAP = {
    PLUS: PLUS,
    NEUTRAL: MINUS,
    MINUS: MINUS,
  }
  def Update(self):
    in_state = self._input.GetState()
    self.SetOutputState(GateIsHigh.LOGIC_MAP[in_state])

class GateIsNeutral(GateMonadic):
  """
  in  | out
  (-) | (-)
  (0) | (+)
  (+) | (-)
  """
  LOGIC_MAP = {
    PLUS: MINUS,
    NEUTRAL: PLUS,
    MINUS: MINUS,
  }
  def Update(self):
    in_state = self._input.GetState()
    self.SetOutputState(GateIsNeutral.LOGIC_MAP[in_state])

class GateIsLow(GateMonadic):
  """
  in  | out
  (-) | (+)
  (0) | (-)
  (+) | (-)
  """
  LOGIC_MAP = {
    PLUS: MINUS,
    NEUTRAL: MINUS,
    MINUS: PLUS,
  }
  def Update(self):
    in_state = self._input.GetState()
    self.SetOutputState(GateIsLow.LOGIC_MAP[in_state])


class GateDiadic:
  def __init__(self):
    self._input1 = ConnectionPoint(ConnectionPoint.READER, self)
    self._input2 = ConnectionPoint(ConnectionPoint.READER, self)
    self._output = ConnectionPoint(ConnectionPoint.WRITER, self)
    self._delay = 0

  def SetInputWire1(self, wire):
    wire.Connect(self._input1)

  def SetInputWire2(self, wire):
    wire.Connect(self._input2)

  def SetOutputWire(self, wire):
    wire.Connect(self._output)

  def SetOutputState(self, state):
    # Output is already at the current state, no need to do anything.
    if self._output.GetState() == state: return

    if DELAY_ENABLED:
      Timer(self._delay, lambda: self._output.SetStateWrite(state))
    else:
      self._output.SetStateWrite(state)

  def Update(self):
    raise NotImplementedError('Update not implemented for %s' % type(self).__name__)

  def __str__(self):
    return '%s<I1: %s, I2: %s, O: %s>' % \
        (type(self).__name__, self._input1.State(), self._input2.State(), self._output.State())


class GateAnd(GateDiadic):
  """
  Equivalent to a minimum function
        (+) (0) (-)
      +-------------
  (+) | (+) (0) (-)
  (0) | (0) (0) (-)
  (-) | (-) (-) (-)
  """
  def Update(self):
    read1 = self._input1.GetState()
    read2 = self._input2.GetState()
    value = PLUS
    if read1 is MINUS or read2 is MINUS:
      value = MINUS
    elif read1 is NEUTRAL or read2 is NEUTRAL:
      value = NEUTRAL
    self.SetOutputState(value)


class GateNand(GateAnd):
  def SetOutputState(self, value):
    super().SetOutputState(GateNegate.LOGIC_MAP[value])

class GateOr(GateDiadic):
  """
  Equivalent to a maximum function
        (+) (0) (-)
      +-------------
  (+) | (+) (+) (+)
  (0) | (+) (0) (0)
  (-) | (+) (0) (-)
  """
  def Update(self):
    read1 = self._input1.GetState()
    read2 = self._input2.GetState()
    value = MINUS
    if read1 is PLUS or read2 is PLUS:
      value = PLUS
    elif read1 is NEUTRAL or read2 is NEUTRAL:
      value = NEUTRAL
    self.SetOutputState(value)

class GateNor(GateOr):
  def SetOutputState(self, value):
    super().SetOutputState(GateNegate.LOGIC_MAP[value])

class GateXor(GateDiadic):
  """
  (0) if either is (0),
  (+) if different
  (-) if same
        (+) (0) (-)
      +-------------
  (+) | (-) (0) (+)
  (0) | (0) (0) (0)
  (-) | (+) (0) (-)
  """
  def Update(self):
    read1 = self._input1.GetState()
    read2 = self._input2.GetState()
    value = MINUS
    if read1 is NEUTRAL or read2 is NEUTRAL:
      value = NEUTRAL
    elif read1 is not read2:
      value = PLUS
    self.SetOutputState(value)

class GateXnor(GateXor):
  def SetOutputState(self, value):
    super().SetOutputState(GateNegate.LOGIC_MAP[value])


class GateConsensus(GateDiadic):
  """
  (-) if both are (-)
  (+) if both are (+)
  (0) otherwise

        (+) (0) (-)
      +-------------
  (+) | (+) (0) (0)
  (0) | (0) (0) (0)
  (-) | (0) (0) (-)
  """
  def Update(self):
    read1 = self._input1.GetState()
    read2 = self._input2.GetState()
    value = read1 == read2 and read1 or NEUTRAL
    self.SetOutputState(value)


class GateSum(GateDiadic):
  """
  Adder Gate, includes an overflow as well
        (+) (0) (-)
      +-------------
  (+) | (-) (+) (0)
  (0) | (+) (0) (-)
  (-) | (0) (-) (+)

  Overflow logic is that of consensus
        (+) (0) (-)
      +-------------
  (+) | (+) (0) (0)
  (0) | (0) (0) (0)
  (-) | (0) (0) (-)

  """
  LOGIC_MAP = {
    (PLUS, PLUS): MINUS,
    (PLUS, NEUTRAL): PLUS,
    (PLUS, MINUS): NEUTRAL,
    (NEUTRAL, PLUS): PLUS,
    (NEUTRAL, NEUTRAL): NEUTRAL,
    (NEUTRAL, MINUS): MINUS,
    (MINUS, PLUS): NEUTRAL,
    (MINUS, NEUTRAL): MINUS,
    (MINUS, MINUS): PLUS,
  }

  def __init__(self):
    super().__init__()
    self._overflow = ConnectionPoint(ConnectionPoint.WRITER)

  def SetOverflowWire(self, wire):
    wire.Connect(self._overflow)

  def Update(self):
    read1 = self._input1.GetState()
    read2 = self._input2.GetState()
    overflow = read1 == read2 and read1 or NEUTRAL
    self.SetOutputState(GateSum.LOGIC_MAP[(read1, read2)])
    self.SetOverflowState(overflow)

  def SetOverflowState(self, state):
    # Output is already at the current state, no need to do anything.
    if self._overflow.GetState() == state: return

    if DELAY_ENABLED:
      Timer(self._delay, lambda: self._overflow.SetStateWrite(state))
    else:
      self._overflow.SetStateWrite(state)


class GateSumAlternate(GateSum):
  """
  Alternate version of GateSum whose logic is completely built off of other
  gates.
  Key:
    a    : input1
    b    : input2
    = -1 : GateIsLow
    - 1  : GateDecrement
    ^    : GateAnd
    = 0  : GateIsNeutral
    = 1  : GateIsHigh
    + 1  : GateIncrement
    v    : GateOr
    sum  : output

  sum = ((a = -1) ^ (b - 1)) v ((a = 0) ^ b) v ((a = 1) ^ (b + 1))
  overflow = consensus(a, b)
  """
  def __init__(self):
    super().__init__()
    wires = [Wire() for i in range(11)]
    # a
    self._identity_a = GateIdentity()
    self._identity_a.SetOutputWire(wires[0])
    # b
    self._identity_b = GateIdentity()
    self._identity_b.SetOutputWire(wires[1])

    # A = (a = -1) ^ (b - 1)
    lowA = GateIsLow()
    lowA.SetInputWire(wires[0])
    lowA.SetOutputWire(wires[2])
    lowDec = GateDecrement()
    lowDec.SetInputWire(wires[1])
    lowDec.SetOutputWire(wires[3])
    lowAnd = GateAnd()
    lowAnd.SetInputWire1(wires[2])
    lowAnd.SetInputWire2(wires[3])
    lowAnd.SetOutputWire(wires[4])

    # B = (a = 0) ^ b
    midMid = GateIsNeutral()
    midMid.SetInputWire(wires[0])
    midMid.SetOutputWire(wires[5])
    midAnd = GateAnd()
    midAnd.SetInputWire1(wires[5])
    midAnd.SetInputWire2(wires[1])
    midAnd.SetOutputWire(wires[6])

    # C = (a = 1) ^ (b + 1)
    highA = GateIsHigh()
    highA.SetInputWire(wires[0])
    highA.SetOutputWire(wires[7])
    highInc = GateIncrement()
    highInc.SetInputWire(wires[1])
    highInc.SetOutputWire(wires[8])
    highAnd = GateAnd()
    highAnd.SetInputWire1(wires[7])
    highAnd.SetInputWire2(wires[8])
    highAnd.SetOutputWire(wires[9])

    # A v B
    or1 = GateOr()
    or1.SetInputWire1(wires[4])
    or1.SetInputWire2(wires[6])
    or1.SetOutputWire(wires[10])

    # (A v B) v C
    self._output_gate = GateOr()
    self._output_gate.SetInputWire1(wires[9])
    self._output_gate.SetInputWire2(wires[10])

    # Consensus is the equivalent of an overflow/underflow
    self._overflow_gate = GateConsensus()
    self._overflow_gate.SetInputWire1(wires[0])
    self._overflow_gate.SetInputWire2(wires[1])


  def SetInputWire1(self, wire):
    self._identity_a.SetInputWire(wire)

  def SetInputWire2(self, wire):
    self._identity_b.SetInputWire(wire)

  def SetOutputWire(self, wire):
    self._output_gate.SetOutputWire(wire)

  def SetOverflowWire(self, wire):
    self._overflow_gate.SetOutputWire(wire)

  def Update(self):
    pass

  def SetOverflowState(self):
    pass


class GateMem(GateDiadic):
  """ A gate that reads from I1 if I2 is (+), no change if I2 is (0), or negates
      if I2 is (-)

        (+) (0) (-)
      +-------------
  (+) | (+) (0) (-)
  (0) |  x   x   x 
  (-) | (-) (0) (+)

  """
  def Update(self):
    read2 = self._input2.GetState()
    if read2 == NEUTRAL:
      return

    read1 = self._input1.GetState()
    if read2 == PLUS:
      self.SetOutputState(read1)
    else:
      self.SetOutputState(GateNegate.LOGIC_MAP[read1])

class Tryte():
  def __init__(self):
    self._mems = [GateMem() for i in range(9)]
    self._read = GateIdentity()
    wire = Wire()
    self._read.SetOutputWire(wire)

    for mem in self._mems:
      mem.SetInputWire2(wire)

  def SetInputWireAt(self, idx, wire):
    try:
      mem = self._mems[idx]
      mem.SetInputWire1(wire)
    except IndexError as e:
      raise ConnectionError('Index not in range [0,8]: %d' % idx)

  def SetInputWires(self, wires):
    if len(wires) is not len(self._mems):
      raise ConnectionError('Cannot attach %d wires to %d memory inputs' % (len(wires), len(self._mems)))
    for (wire, mem) in zip(wires, self._mems):
      mem.SetInputWire1(wire)

  def SetOutputWireAt(self, idx, wire):
    try:
      mem = self._mems[idx]
      mem.SetOutputWire(wire)
    except IndexError as e:
      raise ConnectionError('Index not in range [0,8]: %d' % idx)

  def SetOutputWires(self, wires):
    if len(wires) is not len(self._mems):
      raise ConnectionError('Cannot attach %d wires to %d memory inputs' % (len(wires), len(self._mems)))
    for (wire, mem) in zip(wires, self._mems):
      mem.SetOutputWire(wire)

  def SetReadWire(self, wire):
    self._read.SetInputWire(wire)


if __name__ == '__main__':
  print('Done loading gates!')
