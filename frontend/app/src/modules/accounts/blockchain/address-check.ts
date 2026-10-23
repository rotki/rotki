import { blake2b } from '@noble/hashes/blake2';
import { sha256 } from '@noble/hashes/sha2';
import { Blockchain } from '@rotki/common';
import { base58, bech32, bech32m, utf8 } from '@scure/base';

/**
 * What the backend makes of one typed entry, decided without asking it.
 *
 * Each check mirrors the backend's own validator for that chain (`_validate_blockchain_account_schemas`
 * in `api/v1/schemas.py`), checksums included, so an entry judged an address cannot be refused for
 * its form and one judged invalid would be refused. Drifting from the backend in either direction
 * is a bug: too strict blocks an address the user can add, too lenient closes the dialog on input
 * the backend then rejects.
 */
export const AddressVerdict = {
  /** An address the backend accepts as it is. */
  ADDRESS: 'address',
  /** A name the backend resolves inside the addition, which only it can answer. */
  NAME: 'name',
  /** Input the backend refuses. */
  INVALID: 'invalid',
} as const;

export type AddressVerdict = (typeof AddressVerdict)[keyof typeof AddressVerdict];

export type AddressCheck = (entry: string) => AddressVerdict;

/** Version bytes of the bitcoin mainnet P2PKH and P2SH base58 addresses, also legacy BCH. */
const BTC_BASE58_VERSIONS: ReadonlySet<number> = new Set([0x00, 0x05]);

/** Version bytes of the dogecoin mainnet P2PKH ("D...") and P2SH ("9..." or "A...") addresses. */
const DOGE_BASE58_VERSIONS: ReadonlySet<number> = new Set([0x1E, 0x16]);

/** A version byte, a 20-byte hash and a 4-byte checksum. */
const BASE58_ADDRESS_BYTES = 25;

const SEGWIT_HRP = 'bc';

const CASHADDR_PREFIX = 'bitcoincash';

const CASHADDR_CHARSET = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l';

const CASHADDR_GENERATOR: readonly bigint[] = [0x98F2BC8E61n, 0x79B76D99E2n, 0xF33E5FB3C4n, 0xAE2EABE2A8n, 0x1E4F43E470n];

const SS58_CHECKSUM_PREFIX = utf8.decode('SS58PRE');

/** Network formats ss58 reserves, which no address may carry. */
const SS58_RESERVED_FORMATS: ReadonlySet<number> = new Set([46, 47]);

const POLKADOT_SS58_FORMAT = 0;

const KUSAMA_SS58_FORMAT = 2;

const HEX_ADDRESS = /^(?:0[Xx])?[\dA-Fa-f]{40}$/;

/** Every separator ENS normalisation reads as a dot, so a name typed with any of them may resolve. */
const NAME_SEPARATOR = /[.。．｡]/;

/**
 * The backend's `TLD_PATTERN`, a top-level domain of two or more characters, after labels that are
 * not empty, since normalisation refuses an empty one.
 */
const NAME_TLD = /^(?:[^.]+\.)+[\da-z-]{2,}$/i;

const PRINTABLE_ASCII = /^[!-~]+$/;

function decodeBase58(value: string): Uint8Array | undefined {
  try {
    return base58.decode(value);
  }
  catch {
    return undefined;
  }
}

function equalBytes(a: Uint8Array, b: Uint8Array): boolean {
  return a.length === b.length && a.every((byte, index) => byte === b[index]);
}

/**
 * A base58check address with one of the given version bytes, written the one way it encodes.
 *
 * @remarks
 * Mirrors the backend's `is_valid_base58_address`, including its final re-encode, which refuses a
 * spelling that decodes to the right bytes but is not the canonical one.
 */
function isBase58CheckAddress(value: string, versions: ReadonlySet<number>): boolean {
  if (value.length < 25 || value.length > 35)
    return false;

  const bytes = decodeBase58(value);
  if (bytes?.length !== BASE58_ADDRESS_BYTES || !versions.has(bytes[0]))
    return false;

  const checksum = sha256(sha256(bytes.subarray(0, -4))).subarray(0, 4);
  return equalBytes(checksum, bytes.subarray(-4)) && base58.encode(bytes) === value;
}

/** The witness version and program of a mainnet segwit address, read with the given checksum. */
function segwitProgram(coder: typeof bech32, value: string): { version: number; program: Uint8Array } | undefined {
  const decoded = coder.decodeUnsafe(value, false);
  if (!decoded || decoded.prefix !== SEGWIT_HRP || decoded.words.length === 0)
    return undefined;

  const [version, ...words] = decoded.words;
  const program = coder.fromWordsUnsafe(words);
  if (!program || program.length < 2 || program.length > 40 || version > 16)
    return undefined;

  return { program, version };
}

/**
 * A segwit address under BIP-173 or BIP-350.
 *
 * @remarks
 * The backend accepts both, as `is_valid_bech32_address` and `is_valid_bech32_bip350_address`: a
 * BIP-173 checksum is accepted for any witness version, with version 0 holding 20 or 32 bytes, and
 * a BIP-350 checksum only for versions 1 to 16.
 */
function isSegwitAddress(value: string): boolean {
  const bip173 = segwitProgram(bech32, value);
  if (bip173 && (bip173.version !== 0 || bip173.program.length === 20 || bip173.program.length === 32))
    return true;

  const bip350 = segwitProgram(bech32m, value);
  return bip350 !== undefined && bip350.version !== 0;
}

function isBtcAddress(value: string): boolean {
  return isBase58CheckAddress(value, BTC_BASE58_VERSIONS) || isSegwitAddress(value);
}

function cashAddrPolymod(values: readonly number[]): bigint {
  let checksum = 1n;
  for (const value of values) {
    const top = checksum >> 35n;
    checksum = ((checksum & 0x07FFFFFFFFn) << 5n) ^ BigInt(value);
    CASHADDR_GENERATOR.forEach((generator, index) => {
      if ((top >> BigInt(index)) & 1n)
        checksum ^= generator;
    });
  }
  return checksum ^ 1n;
}

/**
 * The 5-bit words after the `bitcoincash:` prefix, which may be left out, with the prefix as written.
 * One case throughout, as the backend requires.
 */
function cashAddrWords(value: string): { prefix: string; words: number[] } | undefined {
  if (value !== value.toLowerCase() && value !== value.toUpperCase())
    return undefined;

  const lowered = value.toLowerCase();
  const colons = lowered.split(':').length - 1;
  if (colons > 1)
    return undefined;

  const [prefix, encoded] = (colons === 0 ? `${CASHADDR_PREFIX}:${lowered}` : lowered).split(':');
  if (prefix !== CASHADDR_PREFIX || encoded.length < 8)
    return undefined;

  const words = Array.from(encoded, char => CASHADDR_CHARSET.indexOf(char));
  return words.includes(-1) ? undefined : { prefix, words };
}

/** A Bitcoin Cash CashAddr, with or without its `bitcoincash:` prefix, as `is_valid_bitcoin_cash_address`. */
function isCashAddress(value: string): boolean {
  const parsed = cashAddrWords(value);
  if (!parsed)
    return false;

  const { prefix, words } = parsed;
  const expandedPrefix = Array.from(prefix, char => char.charCodeAt(0) & 0x1F);
  if (cashAddrPolymod([...expandedPrefix, 0, ...words]) !== 0n)
    return false;

  const payloadWords = words.slice(0, -8);
  const payload = bech32.fromWordsUnsafe(payloadWords);
  return payloadWords.length > 0 && payload?.length === 21 && (payload[0] === 0 || payload[0] === 8);
}

function isBchAddress(value: string): boolean {
  return isCashAddress(value) || isBase58CheckAddress(value, BTC_BASE58_VERSIONS);
}

function isSolanaAddress(value: string): boolean {
  return decodeBase58(value)?.length === 32;
}

/** How many checksum bytes an ss58 address of this decoded length carries, as scalecodec's `ss58_decode`. */
function ss58ChecksumLength(length: number, formatLength: number): number | undefined {
  if ([3, 4, 6, 10].includes(length))
    return 1;
  if ([5, 7, 11, 34 + formatLength, 35 + formatLength].includes(length))
    return 2;
  if ([8, 12].includes(length))
    return 3;
  if ([9, 13].includes(length))
    return 4;
  if (length >= 14 && length <= 17)
    return length - 9;
  return undefined;
}

/** The network an ss58 address names, in one byte or two, and how many bytes it takes. */
function ss58Format(bytes: Uint8Array): { network: number; length: number } | undefined {
  if (bytes.length === 0)
    return undefined;

  if ((bytes[0] & 0x40) === 0)
    return { length: 1, network: bytes[0] };

  if (bytes.length < 2)
    return undefined;

  return { length: 2, network: ((bytes[0] & 0x3F) << 2) | (bytes[1] >> 6) | ((bytes[1] & 0x3F) << 8) };
}

/**
 * An ss58 address of the given network, as scalecodec's `is_valid_ss58_address`.
 *
 * @remarks
 * A `0x` public key is refused there, and so here. The checksum is the head of a 64-byte blake2b
 * digest of `SS58PRE` and the address bytes before it.
 */
function isSs58Address(value: string, network: number): boolean {
  if (value.startsWith('0x'))
    return false;

  const bytes = decodeBase58(value);
  const format = bytes && ss58Format(bytes);
  if (!bytes || !format || SS58_RESERVED_FORMATS.has(format.network) || format.network !== network)
    return false;

  const checksumLength = ss58ChecksumLength(bytes.length, format.length);
  if (checksumLength === undefined)
    return false;

  const body = bytes.subarray(0, -checksumLength);
  const digest = blake2b(new Uint8Array([...SS58_CHECKSUM_PREFIX, ...body]), { dkLen: 64 });
  return equalBytes(digest.subarray(0, checksumLength), bytes.subarray(-checksumLength));
}

/**
 * Whether an entry might be an ENS name. Only the backend can say whether it is one, by resolving it.
 *
 * @remarks
 * The backend matches its top-level domain pattern against the normalised name. Normalising printable
 * ASCII only lowercases it, so the pattern can be matched here as typed; anything else may normalise
 * into a name, so whatever has a separator in it is left to the backend rather than refused.
 */
function mayBeName(value: string): boolean {
  return PRINTABLE_ASCII.test(value) ? NAME_TLD.test(value) : NAME_SEPARATOR.test(value);
}

function cannotBeName(): boolean {
  return false;
}

function verdictOf(isAddress: (value: string) => boolean, isName: (value: string) => boolean): AddressCheck {
  return (entry) => {
    if (isAddress(entry))
      return AddressVerdict.ADDRESS;
    return isName(entry) ? AddressVerdict.NAME : AddressVerdict.INVALID;
  };
}

/**
 * The check for entries added to a chain, or nothing for a chain the form cannot judge, which then
 * leaves every entry to the backend.
 *
 * @remarks
 * `takesHex` says whether the chain takes hex addresses: an EVM or EVM-like chain, or every EVM
 * chain at once. Bitcoin Cash takes only names ending in `.eth`, which the backend checks before
 * anything else; Solana and Dogecoin take no names at all.
 */
export function addressCheckFor(chain: string, takesHex: boolean): AddressCheck | undefined {
  if (takesHex)
    return verdictOf(value => HEX_ADDRESS.test(value), mayBeName);

  switch (chain) {
    case Blockchain.BTC:
      return verdictOf(isBtcAddress, mayBeName);
    case Blockchain.BCH:
      return verdictOf(isBchAddress, value => value.endsWith('.eth'));
    case Blockchain.DOGE:
      return verdictOf(value => isBase58CheckAddress(value, DOGE_BASE58_VERSIONS), cannotBeName);
    case Blockchain.SOLANA:
      return verdictOf(isSolanaAddress, cannotBeName);
    case Blockchain.DOT:
      return verdictOf(value => isSs58Address(value, POLKADOT_SS58_FORMAT), mayBeName);
    case Blockchain.KSM:
      return verdictOf(value => isSs58Address(value, KUSAMA_SS58_FORMAT), mayBeName);
    default:
      return undefined;
  }
}
