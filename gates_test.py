from gates import *
import unittest

class TestConnections(unittest.TestCase):
  def testWire_ConnectionsImpactEachOther(self):
    writing = ConnectionPoint(ConnectionPoint.WRITER, state=NEUTRAL)
    reading = ConnectionPoint(ConnectionPoint.READER, state=PLUS)
    ignoring = ConnectionPoint(ConnectionPoint.HIGH_IMPEDANCE, state=MINUS)

    wire_1 = Wire()
    wire_1.Connect(writing)
    wire_1.Connect(reading)
    wire_1.Connect(ignoring)
    wire_1.Update()

    self.assertEqual(NEUTRAL, writing.GetState(), 'Writer should not change')
    self.assertEqual(NEUTRAL, reading.GetState(), 'Reader should change to writer value')
    self.assertEqual(MINUS, ignoring.GetState(), 'High Impedance should not change')


class TestMonadicGates(unittest.TestCase):
  def setupMonadic(self, gate_class):
    writer = ConnectionPoint(ConnectionPoint.WRITER, state=NEUTRAL)
    wire_1 = Wire()
    gate = gate_class()
    wire_2 = Wire()
    reader = ConnectionPoint(ConnectionPoint.READER, state=NEUTRAL)

    wire_1.Connect(writer)
    gate.SetInputWire(wire_1)
    gate.SetOutputWire(wire_2)
    wire_2.Connect(reader)
    wire_1.Update()
    wire_2.Update()

    return (writer, reader)

  def genericMonadicTest(self, gate_type, in_outs):
    writer, reader = self.setupMonadic(gate_type)
    for set_value in in_outs:
      expectation = in_outs[set_value]
      writer.SetStateWrite(set_value)
      result = reader.GetState()
      self.assertEqual(expectation, result, '%s with input %s should be %s, but was %s' % (
        gate_type.__name__, STATE_NAME[set_value], STATE_NAME[expectation], STATE_NAME[result]))

  def testGateIdentity(self):
    self.genericMonadicTest(GateIdentity, {
      PLUS: PLUS,
      NEUTRAL: NEUTRAL,
      MINUS: MINUS,
    })

  def testGateIncrement(self):
    self.genericMonadicTest(GateIncrement, {
      PLUS: MINUS,
      NEUTRAL: PLUS,
      MINUS: NEUTRAL,
    })

  def testGateDecrement(self):
    self.genericMonadicTest(GateDecrement, {
      PLUS: NEUTRAL,
      NEUTRAL: MINUS,
      MINUS: PLUS,
    })

  def testGateNegate(self):
    self.genericMonadicTest(GateNegate, {
      PLUS: MINUS,
      NEUTRAL: NEUTRAL,
      MINUS: PLUS,
    })


class TestDiadicGates(unittest.TestCase):
  def setupDiadicGate(self, gate_type):
    writer_1 = ConnectionPoint(ConnectionPoint.WRITER)
    wire_1 = Wire()
    writer_2 = ConnectionPoint(ConnectionPoint.WRITER)
    wire_2 = Wire()
    gate = gate_type()
    wire_3 = Wire()
    reader = ConnectionPoint(ConnectionPoint.READER)

    wire_1.Connect(writer_1)
    wire_2.Connect(writer_2)

    gate.SetInputWire1(wire_1)
    gate.SetInputWire2(wire_2)

    wire_3.Connect(reader)
    gate.SetOutputWire(wire_3)

    return (writer_1, writer_2, reader, gate)

  def genericDiadicTest(self, gate_type, ins_outs):
    (i1, i2, o, g) = self.setupDiadicGate(gate_type)
    for (in1, in2) in ins_outs:
      expected = ins_outs[(in1, in2)]
      i1.SetStateWrite(in1)
      i2.SetStateWrite(in2)

      result = o.GetState()
      self.assertEqual(expected, result, '%s expected output [%s]' % (g, STATE_NAME[result]))

  def testGateAnd(self):
    self.genericDiadicTest(GateAnd, {
      (PLUS, PLUS): PLUS,
      (PLUS, NEUTRAL): NEUTRAL,
      (PLUS, MINUS): MINUS,
      (NEUTRAL, NEUTRAL): NEUTRAL,
      (NEUTRAL, MINUS): MINUS,
      (MINUS, MINUS): MINUS,
    })

  def testGateNand(self):
    self.genericDiadicTest(GateNand, {
      (PLUS, PLUS): MINUS,
      (PLUS, NEUTRAL): NEUTRAL,
      (PLUS, MINUS): PLUS,
      (NEUTRAL, NEUTRAL): NEUTRAL,
      (NEUTRAL, MINUS): PLUS,
      (MINUS, MINUS): PLUS,
    })

  def testGateOr(self):
    self.genericDiadicTest(GateOr, {
      (PLUS, PLUS): PLUS,
      (PLUS, NEUTRAL): PLUS,
      (PLUS, MINUS): PLUS,
      (NEUTRAL, NEUTRAL): NEUTRAL,
      (NEUTRAL, MINUS): NEUTRAL,
      (MINUS, MINUS): MINUS,
    })

  def testGateNor(self):
    self.genericDiadicTest(GateNor, {
      (PLUS, PLUS): MINUS,
      (PLUS, NEUTRAL): MINUS,
      (PLUS, MINUS): MINUS,
      (NEUTRAL, NEUTRAL): NEUTRAL,
      (NEUTRAL, MINUS): NEUTRAL,
      (MINUS, MINUS): PLUS,
    })

  def testGateXor(self):
    self.genericDiadicTest(GateXor, {
      (PLUS, PLUS): MINUS,
      (PLUS, NEUTRAL): NEUTRAL,
      (PLUS, MINUS): PLUS,
      (NEUTRAL, NEUTRAL): NEUTRAL,
      (NEUTRAL, MINUS): NEUTRAL,
      (MINUS, MINUS): MINUS,
    })

  def testGateXnor(self):
    self.genericDiadicTest(GateXnor, {
      (PLUS, PLUS): PLUS,
      (PLUS, NEUTRAL): NEUTRAL,
      (PLUS, MINUS): MINUS,
      (NEUTRAL, NEUTRAL): NEUTRAL,
      (NEUTRAL, MINUS): NEUTRAL,
      (MINUS, MINUS): PLUS,
    })

  def testGateSum(self):
    writer_1, writer_2, reader, gate = self.setupDiadicGate(GateSum)

    reader_overflow = ConnectionPoint(ConnectionPoint.READER)
    wire = Wire()
    wire.Connect(reader_overflow)
    gate.SetOverflowWire(wire)

    expectations = {
      (PLUS,    PLUS):    (MINUS,   PLUS),
      (PLUS,    NEUTRAL): (PLUS,    NEUTRAL),
      (PLUS,    MINUS):   (NEUTRAL, NEUTRAL),
      (NEUTRAL, NEUTRAL): (NEUTRAL, NEUTRAL),
      (NEUTRAL, MINUS):   (MINUS,   NEUTRAL),
      (MINUS,   MINUS):   (PLUS,    MINUS),
    }

    for (in1, in2) in expectations:
      (output, overflow) = expectations[(in1, in2)]
      writer_1.SetStateWrite(in1)
      writer_2.SetStateWrite(in2)

      result = reader.GetState()
      result_over = reader_overflow.GetState()
      self.assertEqual(output, result, '%s expected %s' % (gate, STATE_NAME[output]))
      self.assertEqual(overflow, result_over, '%s expected overflow %s, but got %s' % \
          (gate, STATE_NAME[overflow], STATE_NAME[result_over]))

    writer_1_a, writer_2_a, reader_a, gate_a = self.setupDiadicGate(GateSumAlternate)

    reader_overflow_a = ConnectionPoint(ConnectionPoint.READER)
    wire_a = Wire()
    wire_a.Connect(reader_overflow_a)
    gate_a.SetOverflowWire(wire_a)

    for (in1, in2) in expectations:
      writer_1.SetStateWrite(in1)
      writer_1_a.SetStateWrite(in1)

      writer_2.SetStateWrite(in2)
      writer_2_a.SetStateWrite(in2)

      result = reader.GetState()
      result_a = reader_a.GetState()

      result_over = reader_overflow.GetState()
      result_over_a = reader_overflow_a.GetState()

      self.assertEqual(result, result_a, '%s and %s have conflicting outputs' % (gate, gate_a))
      self.assertEqual(result_over, result_over_a, '%s and %s have conflicting overflows' % (gate, gate_a))

  def testGateMem(self):
    (writer_1, writer_2, output, gate) = self.setupDiadicGate(GateMem)
    expectations = [
        (NEUTRAL, NEUTRAL, NEUTRAL),
        (PLUS,    NEUTRAL, NEUTRAL),
        (PLUS,    PLUS,    PLUS),
        (PLUS,    MINUS,   MINUS),
        (NEUTRAL, MINUS,   NEUTRAL),
        (MINUS,   MINUS,   PLUS),
        (MINUS,   NEUTRAL, PLUS),
        (NEUTRAL, NEUTRAL, PLUS),
        (NEUTRAL, PLUS,    NEUTRAL),
        (MINUS,   PLUS,    MINUS),
        (MINUS,   NEUTRAL, MINUS),
        (NEUTRAL, NEUTRAL, MINUS),
    ]

    for (in1, in2, out) in expectations:
      writer_1.SetStateWrite(in1)
      writer_2.SetStateWrite(in2)

      result = output.GetState()
      self.assertEqual(out, result, '%s expected %s' %  (gate, STATE_NAME[out]))


class TestTryte(unittest.TestCase):
  def setupTryte(self):
    tryte = Tryte()
    writers = [ConnectionPoint(ConnectionPoint.WRITER) for i in range(9)]
    readers = [ConnectionPoint(ConnectionPoint.READER) for i in range(9)]
    inwires = [Wire() for i in range(9)]
    outwires = [Wire() for i in range(9)]
    for (writer, inwire) in zip(writers, inwires):
      inwire.Connect(writer)
    for (reader, outwire) in zip(readers, outwires):
      outwire.Connect(reader)

    readwire = Wire()
    readflag = ConnectionPoint(ConnectionPoint.WRITER)
    readwire.Connect(readflag)

    tryte.SetInputWires(inwires)
    tryte.SetOutputWires(outwires)
    tryte.SetReadWire(readwire)

    return (tryte, writers, readflag, readers)

  def testTrye_InputsRead(self):
    tryte, writers, readflag, readers = self.setupTryte()

    # Clear the tryte by setting everything to neutral and the read flag to (+)
    for writer in writers:
      writer.SetStateWrite(NEUTRAL)
    readflag.SetStateWrite(PLUS)
    for reader in readers:
      self.assertEqual(NEUTRAL, reader.GetState(), 'Everything should be (0)')

    # Turn read flag off, so change to write shouldn't affect anything.
    readflag.SetStateWrite(NEUTRAL)
    for writer in writers:
      writer.SetStateWrite(PLUS)

    for reader in readers:
      self.assertEqual(NEUTRAL, reader.GetState(), 'Everything should still be (0)')

    # Turn read flag on, suddenly everything is changed.
    readflag.SetStateWrite(PLUS)
    for reader in readers:
      self.assertEqual(PLUS, reader.GetState(), 'Everything should be changed to (+)')

    # Change read flag to inverse, everything is changed to inverse.
    readflag.SetStateWrite(MINUS)
    for reader in readers:
      self.assertEqual(MINUS, reader.GetState(), 'Everything should be changed to (-)')

    readflag.SetStateWrite(NEUTRAL)
    for writer in writers:
      writer.SetStateWrite(NEUTRAL)

    for reader in readers:
      self.assertEqual(MINUS, reader.GetState(), 'Everything should still be (-)')


class MockTimer:
  nextfn = False
  expected_period = False
  def __init__(self, period, fn):
    assert MockTimer.expected_period == period, \
        'Periods are not equal, %f != %f' % (MockTimer.expected_period, period)
    self.period = period
    MockTimer.nextfn = fn
  def start(self):
    pass

  def RunFunc():
    if MockTimer.nextfn:
      MockTimer.nextfn()
    else:
      MockTimer.nextfn = False

class TestOscillator(unittest.TestCase):
  def testBasicOscillations(self):
    MockTimer.expected_period = 0.25
    oscillator = Oscillator(1, MockTimer)
    expected_values = [
        NEUTRAL, PLUS,
        NEUTRAL, MINUS,
        NEUTRAL, PLUS,
        NEUTRAL, MINUS, 
        NEUTRAL,
    ]

    for i in range(8):
      self.assertEqual(expected_values[i], oscillator.ReadOutput(), \
          '%s at time %d expected %s' % (oscillator, i, STATE_NAME[expected_values[i]]))
      MockTimer.RunFunc()


if __name__ == '__main__':
  unittest.main()