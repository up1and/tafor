"""Tests for the AFTN and file message generators."""

import datetime
import json

from tafor.core.telegram.generator import (
    AFTNDecoder,
    AFTNMessageGenerator,
    FileMessageGenerator,
    aftnPriority,
    fileMessageName,
    linewrap,
)

CRLF = '\r\n'


def aftn(text='TEXT=', **kwargs):
    params = {
        'channel': 'A',
        'number': 1,
        'priority': 'GG',
        'address': 'YUSO3001',
        'originator': 'YUSOYMYX',
    }
    params.update(kwargs)
    return AFTNMessageGenerator(text, **params)


def test_linewrap_leaves_a_short_line_alone():
    assert linewrap(['ABC'], 10) == ['ABC']


def test_linewrap_breaks_a_line_at_the_limit():
    assert linewrap(['A' * 25], 10) == ['AAAAAAAAAA', 'AAAAAAAAAA', 'AAAAA']


def test_linewrap_keeps_blank_lines():
    assert linewrap(['', 'AB'], 10) == ['', 'AB']


def test_sigmet_and_airmet_go_out_as_ff():
    assert aftnPriority('SIGMET', 'anything') == 'FF'
    assert aftnPriority('AIRMET', 'anything') == 'FF'


def test_an_amended_taf_goes_out_as_ff():
    assert aftnPriority('TAF', 'TAF AMD ZJHK 150726Z') == 'FF'
    assert aftnPriority('TAF', 'TAF ZJHK 150726Z') == 'GG'
    assert aftnPriority('METAR', 'METAR ZJHK 150726Z') == 'GG'


def test_file_message_name_carries_the_times_and_padded_number(frozen_time):
    valids = (
        datetime.datetime(2026, 10, 12, 10, 0, 0),
        datetime.datetime(2026, 10, 12, 16, 0, 0),
    )

    name = fileMessageName('ZJHK', valids, 7)

    assert name == (
        '9_OTHE_C_ZJHK_20260610080000_STUB-WTMG-MULT-'
        '20261012100000-20261012160000-XXX-1,00007.txt'
    )


def test_an_aftn_message_is_a_heading_an_address_a_time_and_a_body(frozen_time):
    lines = aftn().toString().split(CRLF)

    assert lines[0] == 'ZCZC A0001'
    assert lines[1] == 'GG YUSO3001'
    # the day and time come from the frozen wall clock
    assert lines[2] == '100800 YUSOYMYX'
    assert lines[3] == 'TEXT='
    assert lines[-4:] == ['', '', '', 'NNNN']


def test_the_sequence_number_is_zero_padded_to_the_sequence_length():
    assert aftn(number=1).messages[0].startswith('ZCZC A0001')
    assert aftn(number=7, sequenceLength=3).messages[0].startswith('ZCZC A007')


def test_a_number_beyond_the_sequence_length_is_wrapped():
    assert aftn(number=10000, sequenceLength=4).messages[0].startswith('ZCZC A0000')


def test_an_address_list_is_split_at_max_send_address():
    generator = aftn(address='A1B2C3D4 E5F6G7H8 I9J0K1L2', maxSendAddress=2)

    assert len(generator.messages) == 2
    assert generator.messages[0].split(CRLF)[1] == 'GG A1B2C3D4 E5F6G7H8'
    assert generator.messages[1].split(CRLF)[1] == 'GG I9J0K1L2'


def test_the_sequence_number_advances_with_each_address_group():
    generator = aftn(address='A1B2C3D4 E5F6G7H8 I9J0K1L2', maxSendAddress=1)

    headings = [message.split(CRLF)[0] for message in generator.messages]
    assert headings == ['ZCZC A0001', 'ZCZC A0002', 'ZCZC A0003']


def test_messages_are_joined_by_four_line_breaks():
    generator = aftn(address='A1B2C3D4 E5F6G7H8 I9J0K1L2', maxSendAddress=2)

    assert generator.toString() == (CRLF * 4).join(generator.messages)


def test_to_json_is_a_json_list_of_the_messages():
    generator = aftn()

    assert json.loads(generator.toJson()) == generator.messages


def test_a_file_message_has_no_priority_or_address_line():
    lines = FileMessageGenerator('LINE1\nLINE2', number=5).toString().split(CRLF)

    assert lines[0] == 'ZCZC 005'
    assert lines[1] == 'LINE1'
    assert lines[2] == 'LINE2'
    assert lines[-4:] == ['', '', '', 'NNNN']


def test_a_file_message_serialises_to_the_same_string():
    generator = FileMessageGenerator('TEXT=', number=1)

    assert generator.toJson() == generator.toString()


def test_the_decoder_reads_back_what_the_generator_wrote():
    generator = aftn(priority='FF', address='YUSO3001 YUSI3002')

    decoder = AFTNDecoder(generator.messages)

    assert decoder.priority == 'FF'
    assert decoder.originator == 'YUSOYMYX'
    assert decoder.address == 'YUSO3001 YUSI3002'


def test_the_decoder_accepts_a_json_string_as_well_as_a_list():
    generator = aftn()

    assert AFTNDecoder(generator.toJson()).priority == 'GG'
    assert AFTNDecoder(generator.messages).priority == 'GG'


def test_the_decoder_collects_addresses_across_every_message():
    generator = aftn(address='A1B2C3D4 E5F6G7H8 I9J0K1L2', maxSendAddress=2)

    assert AFTNDecoder(generator.messages).address == 'A1B2C3D4 E5F6G7H8 I9J0K1L2'


def test_the_decoder_finds_no_priority_when_there_is_none():
    decoder = AFTNDecoder(['ZCZC A0001', '120930 YUSOYMYX', 'TEXT=', 'NNNN'])

    assert decoder.priority is None
