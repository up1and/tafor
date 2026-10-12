"""Tests for the ITA2 (Baudot-Murray) encoder.

The encoder is a shift-state machine: letters and figures share code points,
so a shift code is emitted only when the state actually changes.
"""

import pytest

from tafor.core.telegram.encoder import Figures, ITA2_STANDARD, Letters, encode


def test_the_standard_table_is_the_named_ita2_one():
    assert ITA2_STANDARD.name == "Baudot-Murray code (ITA2), Standard"
    assert ITA2_STANDARD.shifts == {Letters, Figures}


def test_a_letter_opens_letters_shift_before_its_code():
    assert encode("A", ITA2_STANDARD) == b"1f03"
    assert encode("E", ITA2_STANDARD) == b"1f01"


def test_a_digit_opens_figures_shift_before_its_code():
    assert encode("1", ITA2_STANDARD) == b"1b17"
    assert encode("3", ITA2_STANDARD) == b"1b01"


def test_consecutive_letters_share_one_shift_code():
    # only the first letter pays for the Letters shift
    assert encode("AB", ITA2_STANDARD) == b"1f0319"
    assert encode("NOSIG", ITA2_STANDARD) == b"1f0c1805061a"


def test_switching_between_letters_and_figures_emits_both_shifts():
    assert encode("A1", ITA2_STANDARD) == b"1f031b17"
    assert encode("AB1", ITA2_STANDARD) == b"1f03191b17"


def test_returning_to_letters_re_emits_the_letters_shift():
    # 1 leaves the state in Figures, so the trailing A needs Letters again
    assert encode("A1A", ITA2_STANDARD) == b"1f031b171f03"


def test_characters_shared_by_both_shifts_do_not_change_state():
    # space, CR and LF have the same code in both tables
    assert encode(" ", ITA2_STANDARD) == b"04"
    assert encode("\r", ITA2_STANDARD) == b"08"
    assert encode("\n", ITA2_STANDARD) == b"02"
    assert encode("A B", ITA2_STANDARD) == b"1f030419"


def test_lowercase_input_is_upcased_before_encoding():
    assert encode("abc", ITA2_STANDARD) == encode("ABC", ITA2_STANDARD)
    assert encode("AbC", ITA2_STANDARD) == b"1f03190e"


def test_an_empty_string_encodes_to_nothing():
    assert encode("", ITA2_STANDARD) == b""


def test_a_character_outside_the_table_is_rejected():
    for bad in ("@", "#", "\t"):
        with pytest.raises(Exception, match="Unsupported value"):
            encode(bad, ITA2_STANDARD)


def test_a_message_encodes_end_to_end():
    assert encode("01004MPS", ITA2_STANDARD) == b"1b161716160a1f1c1605"

