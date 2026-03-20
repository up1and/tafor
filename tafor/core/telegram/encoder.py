"""
Encode for second-generation Baudot codes
(a.k.a. Baudot-Murray or ITA2)
"""

from collections import namedtuple, defaultdict

Shift = namedtuple('Shift', ('name',))

Letters = Shift('Letters')
Figures = Shift('Figures')

STANDARD_TABLE = {
    Letters: [
        '\x00', 'E', '\n', 'A', ' ', 'S', 'I', 'U',
        '\r', 'D', 'R', 'J', 'N', 'F', 'C', 'K',
        'T', 'Z', 'L', 'W', 'H', 'Y', 'P', 'Q',
        'O', 'B', 'G', Figures, 'M', 'X', 'V', Letters
    ],
    Figures: [
        '\x00', '3', '\n', '-', ' ', "'", '8', '7',
        '\r', '\x05', '4', '\x07', ',', '!', ':', '(',
        '5', '+', ')', '2', '$', '6', '0', '1',
        '9', '?', '&', Figures, '.', '/', '=', Letters
    ],
}

def _makeEncodingTable(tables):
    """
    Generates the encoding tables by reversing the decoding table
    """
    matches = defaultdict(set)
    for shift, table in tables.items():
        for i, value in enumerate(table):
            matches[value].add((i, shift))

    singleMatch, anyMatches, others = {}, {}, {}

    for value, match in matches.items():

        if len(match) == 1:
            singleMatch[value] = match.pop()
            continue

        codes = set(code for code, _ in match)
        if len(codes) == 1 and len(match) == len(tables):
            anyMatches[value] = codes.pop()
            continue

        others[value] = match

    return singleMatch, anyMatches, others

def encode(chars, codec):
    """
    Encode unicode characters from input chars to hex bytes,
    using the given codec.

    :param chars: Strings to encode
    :param codec: Codec to use for encoding
    """
    state = None
    buffers = []
    outputs = []
    chars = chars.upper()

    for char in chars:
        code, newState = codec.encode(char, state)
        buffers.append(code)

        if newState != state:
            stateCode, _ = codec.encode(newState, None)
            buffers.append(stateCode)
            state = newState

        while buffers:
            outputs.append(buffers.pop(-1))

    byte = ''.join(['{:02x}'.format(o) for o in outputs]).encode()
    return byte


class TabledCodec(object):
    """
    Creates a codec based on a character table.

    The input format must be a dictionary of which the keys are the
    possible states (instances of ``Shift``) and the values are lists
    of length 32 exactly, containing characters or shifts.

    The ``Shift`` instances are the only control characters this
    library knows of. Any other must be taken from ASCII/Unicode.
    """

    def __init__(self, name, tables):

        encSingle, encAny, encOthers = _makeEncodingTable(tables)

        self.name = name
        self.shifts = set(tables.keys())
        self.alphabet = set(value
                                    for table in tables.values()
                                    for value in table
                                    if isinstance(value, str))
        self.decodingTable = tables
        self.encodingSingle = encSingle
        self.encodingAny = encAny
        self.encodingOthers = encOthers

    def encode(self, value, state):
        """
        Get the code of the given character of Shift for this codec.

        Actually, this logic returns not only the code but also the
        state required for this code. The current state should also
        be passed so that more complicated cases can be solved.

        :param value: Value (character or state shift) to encode
        :param state: Current state of encoding
        :return: Code for this value, and required state
        """

        # If this value exists (with the same code) in all states,
        # return its code and the state unchanged
        if value in self.encodingAny:
            return self.encodingAny[value], state

        # If the value unambiguously exists in only one state,
        # return its code and the corresponding state
        if value in self.encodingSingle:
            return self.encodingSingle[value]

        if value not in self.encodingOthers:
            raise Exception('Unsupported value {}'.format(value))

        # The logic below handles other cases. This will need more work.
        # TODO
        matches = self.encodingOthers[value]
        try:
            # This logic handles the case where a same character exists
            # in multiple states but with different codes. Just return
            # the code that works with the current state.
            return next((code, st) for code, st in matches if st == state)
        except StopIteration:
            raise NotImplementedError('This char encodes in a weird way.')


ITA2_STANDARD = TabledCodec(
    'Baudot-Murray code (ITA2), Standard',
    STANDARD_TABLE)
