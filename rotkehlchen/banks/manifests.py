"""The manifests of every in-tree bank connector.

Kept apart from the connector modules so that anything needing only the declarative data
(the locations API, the setup UI, the contract tests) does not import connector code.
"""
from typing import Final

from rotkehlchen.banks.constants import FINTS_CONNECTOR, QONTO_CONNECTOR
from rotkehlchen.banks.manifest import (
    AuthPrimitive,
    AuthStep,
    BankAccessTier,
    BankCapability,
    BankManifest,
    SecretField,
)
from rotkehlchen.locations.constants import (
    LOCATION_QONTO,
)

QONTO_MANIFEST: Final = BankManifest(
    connector_identifier=QONTO_CONNECTOR,
    fixed_location=LOCATION_QONTO,
    display_name='Qonto',
    access_tier=BankAccessTier.OFFICIAL_API,
    capabilities=frozenset({BankCapability.BALANCES, BankCapability.TRANSACTIONS}),
    auth_flow=(AuthStep(primitive=AuthPrimitive.STATIC_SECRET),),
    secrets=(
        SecretField(
            slot='api_key',
            label='Login',
            description='The organization login shown next to the API key in the Qonto app',
        ),
        SecretField(
            slot='api_secret',
            label='Secret key',
            description='The secret key generated together with the login',
        ),
    ),
    maintainer='rotki',
    version='1.0.0',
    docs_url='https://docs.qonto.com',
    setup_notes=(
        (
            'In the Qonto web app go to Settings > Integrations & Partners > API key and '
            'generate a key. Qonto shows a login and a secret key: enter the login as the '
            'login and the secret key as the secret key.'
        ),
        (
            'Only one API key exists per organization. Generating a new one revokes the '
            'previous one everywhere it is used, including other tools connected to Qonto.'
        ),
        (
            'The key gives read access to the organization, its bank accounts and their '
            'transactions. rotki only ever reads. Payments need OAuth and strong customer '
            'authentication, which the API key cannot perform.'
        ),
        (
            'The credentials are stored in your encrypted rotki database and sent only to '
            'Qonto, directly from this machine.'
        ),
    ),
)

FINTS_MANIFEST: Final = BankManifest(
    connector_identifier=FINTS_CONNECTOR,
    fixed_location=None,
    display_name='FinTS/HBCI',
    access_tier=BankAccessTier.FINTS,
    capabilities=frozenset({BankCapability.BALANCES, BankCapability.TRANSACTIONS}),
    auth_flow=(
        AuthStep(primitive=AuthPrimitive.USERNAME_PASSWORD),
        AuthStep(primitive=AuthPrimitive.OTP_INPUT, prompt='Enter the TAN shown by your bank'),
        AuthStep(primitive=AuthPrimitive.APP_APPROVAL_POLL, timeout_seconds=300),
        AuthStep(primitive=AuthPrimitive.CHALLENGE_DISPLAY, prompt='Complete the bank challenge and enter its TAN'),  # noqa: E501
    ),
    secrets=(
        SecretField(slot='bank_code', label='Bank code (BLZ)', secret=False),
        SecretField(slot='endpoint', label='FinTS endpoint', description='The HTTPS PIN/TAN URL published by your bank', secret=False),  # noqa: E501
        SecretField(slot='username', label='Online banking username', secret=False),
        SecretField(slot='pin', label='Online banking PIN'),
    ),
    maintainer='rotki',
    version='1.0.0',
    docs_url='https://python-fints.readthedocs.io/en/latest/quickstart.html',
    setup_notes=(
        'Enter the eight-digit BLZ and the HTTPS FinTS PIN/TAN endpoint published by your bank.',
        'rotki connects directly from this machine. The PIN and reusable FinTS state stay in the encrypted user database.',  # noqa: E501
        'Only settled balances and booked transactions are read; rotki never initiates payments.',
    ),
)

BANK_MANIFESTS: Final = {
    QONTO_CONNECTOR: QONTO_MANIFEST,
    FINTS_CONNECTOR: FINTS_MANIFEST,
}
