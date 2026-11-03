import json
from pathlib import Path

import pytest

from rotkehlchen.tests.unit.test_location_catalog import PACKAGED_IMAGES_DIR
from tools.scripts.generate_fints_bank_directory import build_catalog, logo_for

CATALOG = Path(__file__).parents[3] / 'frontend' / 'app' / 'src' / 'modules' / 'banks' / 'fints-bank-directory.json'  # noqa: E501


@pytest.mark.parametrize(('name', 'organisation', 'logo'), [
    ('Volksbank Mittelhessen', 'BVR', 'bank_vr.svg'),
    ('VR-Bank Coburg', 'BVR', 'bank_vr.svg'),
    ('Sparda-Bank Berlin eG', 'BVR', 'bank_sparda.svg'),
    ('Stadtsparkasse München', 'DSGV', 'bank_sparkasse.svg'),
    ('Baden-Württembergische Bank (BW-Bank)', 'DSGV', 'bank_bw_bank.svg'),
    ('Deutsche Kreditbank Berlin (DKB) AG', 'BdB', 'bank_dkb.svg'),
    ('Raiffeisenlandesbank Oberösterreich', 'BdB', None),
    ('Südtiroler Sparkasse AG', 'BdB', None),
    ('GRENKE BANK', 'BVR', None),
])
def test_logo_follows_name_and_banking_group(
        name: str,
        organisation: str,
        logo: str | None,
) -> None:
    assert logo_for(name, organisation) == logo


def test_logo_indexes_the_institution_it_belongs_to() -> None:
    catalog = build_catalog(
        rows=[{
            'BLZ': bank_code,
            'Institut': name,
            'Ort': 'Berlin',
            'Organisation': organisation,
            'PIN/TAN-Zugang URL': endpoint,
        } for bank_code, name, organisation, endpoint in (
            ('10050000', 'Berliner Sparkasse', 'DSGV', 'https://banking-be3.s-fints-pt-be.de/fints30'),
            ('10010010', 'Postbank', 'BdB', 'https://hbci.postbank.de/banking/hbci.do'),
            ('10030400', 'ABK Allgemeine Beamten Bank AG', 'BdB', 'https://fints.example/abk'),
        )],
        version='2026-10-12',
        source_hash='0' * 64,
    )

    assert {
        logo: [catalog['b'][index][0] for index in indices]
        for logo, indices in catalog['g'].items()
    } == {'bank_postbank.svg': ['Postbank'], 'bank_sparkasse.svg': ['Berliner Sparkasse']}


def test_every_catalog_logo_is_packaged_and_every_bank_logo_is_used() -> None:
    catalog = json.loads(CATALOG.read_text(encoding='utf-8'))
    assert set(catalog['g']) == {path.name for path in PACKAGED_IMAGES_DIR.glob('bank_*')}
    assert all(0 <= index < len(catalog['b']) for indices in catalog['g'].values() for index in indices)  # noqa: E501
