"""Declarative description of a bank connector.

The manifest is what the framework knows about a connector without running it: identity,
access tier, capabilities, how it authenticates (as a sequence of framework primitives, so
that the UI implements each primitive once and no connector ships bespoke auth UI), which
secrets it stores in which credential slot, and the user-facing setup notes.
"""
from dataclasses import dataclass, field
from enum import auto
from typing import TYPE_CHECKING, Any, Final, Literal

from rotkehlchen.utils.mixins.enums import SerializableEnumNameMixin

if TYPE_CHECKING:
    from rotkehlchen.types import Location

CredentialSlot = Literal['api_key', 'api_secret', 'passphrase']
CREDENTIAL_SLOTS: Final = ('api_key', 'api_secret', 'passphrase')


class BankAccessTier(SerializableEnumNameMixin):
    """How rotki reaches the bank. Lower is better; the highest available tier is used."""
    FINTS = 0  # the German multi-bank protocol
    OFFICIAL_API = 1  # documented customer API, keyed
    UNOFFICIAL_API = 2  # reverse-engineered app/web API
    SCRAPING = 3
    FILE_ONLY = 4


class BankCapability(SerializableEnumNameMixin):
    BALANCES = auto()
    TRANSACTIONS = auto()
    HOLDINGS = auto()


class AuthPrimitive(SerializableEnumNameMixin):
    """The vocabulary auth flows are declared over. The UI implements each once."""
    STATIC_SECRET = auto()  # a key/secret the user pastes once
    USERNAME_PASSWORD = auto()
    OTP_INPUT = auto()  # user types a one-time code
    APP_APPROVAL_POLL = auto()  # user confirms on a paired device; rotki polls until done
    CHALLENGE_DISPLAY = auto()  # rotki shows a challenge (e.g. photoTAN) the user answers


@dataclass(frozen=True)
class AuthStep:
    """One step of a connector's auth flow"""
    primitive: AuthPrimitive
    timeout_seconds: int | None = None  # for APP_APPROVAL_POLL
    prompt: str | None = None  # for OTP_INPUT / CHALLENGE_DISPLAY: what to ask the user

    def serialize(self) -> dict[str, Any]:
        data: dict[str, Any] = {'primitive': self.primitive.serialize()}
        if self.timeout_seconds is not None:
            data['timeout_seconds'] = self.timeout_seconds
        if self.prompt is not None:
            data['prompt'] = self.prompt
        return data


@dataclass(frozen=True)
class SecretField:
    """A credential the user enters at setup, and the slot it is stored in.

    Slots are the columns of the user_credentials table, so the setup UI can render the
    field generically while the storage stays the one every exchange already uses.
    """
    slot: CredentialSlot
    label: str  # what the bank calls it, e.g. "Login" / "Secret key"
    description: str = ''

    def serialize(self) -> dict[str, Any]:
        return {'slot': self.slot, 'label': self.label, 'description': self.description}


@dataclass(frozen=True)
class BankManifest:
    location: Location
    display_name: str
    access_tier: BankAccessTier
    capabilities: frozenset[BankCapability]
    auth_flow: tuple[AuthStep, ...]
    secrets: tuple[SecretField, ...]
    maintainer: str
    version: str
    docs_url: str
    # user-facing setup notes: where to get the credentials, caveats, confidentiality
    setup_notes: tuple[str, ...] = field(default_factory=tuple)

    def validate(self) -> None:
        """Raise ValueError when the manifest is internally inconsistent.

        Run by the contract test suite for every registered connector.
        """
        if len(self.auth_flow) == 0:
            raise ValueError('auth_flow must declare at least one step')
        if len(self.capabilities) == 0:
            raise ValueError('a connector must declare at least one capability')
        slots = [secret.slot for secret in self.secrets]
        if len(slots) != len(set(slots)):
            raise ValueError(f'credential slots must be unique, got {slots}')
        for slot in slots:
            if slot not in CREDENTIAL_SLOTS:
                raise ValueError(f'unknown credential slot {slot}')
        if 'api_key' not in slots:
            raise ValueError('the api_key slot is required: it is the credential identity')
        uses_static_secret = any(s.primitive == AuthPrimitive.STATIC_SECRET for s in self.auth_flow)  # noqa: E501
        if uses_static_secret and len(self.secrets) == 0:
            raise ValueError('a static_secret auth flow needs at least one secret field')
        for step in self.auth_flow:
            if step.primitive == AuthPrimitive.APP_APPROVAL_POLL and step.timeout_seconds is None:
                raise ValueError('app_approval_poll steps need a timeout')
        if self.version == '' or self.maintainer == '' or self.docs_url == '':
            raise ValueError('version, maintainer and docs_url are required')

    def serialize(self) -> dict[str, Any]:
        return {
            'location': self.location.serialize(),
            'display_name': self.display_name,
            'access_tier': self.access_tier.serialize(),
            'capabilities': sorted(c.serialize() for c in self.capabilities),
            'auth_flow': [step.serialize() for step in self.auth_flow],
            'secrets': [secret.serialize() for secret in self.secrets],
            'maintainer': self.maintainer,
            'version': self.version,
            'docs_url': self.docs_url,
            'setup_notes': list(self.setup_notes),
        }
