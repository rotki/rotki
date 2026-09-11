"""The manifests of every in-tree bank connector.

Kept apart from the connector modules so that anything needing only the declarative data
(the locations API, the setup UI, the contract tests) does not import connector code.
"""
from typing import Final

from rotkehlchen.banks.manifest import (
    AuthPrimitive,
    AuthStep,
    BankAccessTier,
    BankCapability,
    BankManifest,
    SecretField,
)
from rotkehlchen.types import Location

QONTO_MANIFEST: Final = BankManifest(
    location=Location.QONTO,
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

BANK_MANIFESTS: Final = {
    Location.QONTO: QONTO_MANIFEST,
}
