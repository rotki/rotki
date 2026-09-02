export function isValidEthAddress(address?: string): boolean {
  if (!address)
    return false;

  return /^0x[\dA-Fa-f]{40}$/.test(address);
}

const P2PKH_OR_P2SH = /^[13][1-9A-HJ-NP-Za-km-z]{25,34}$/;
const BECH32 = /^bc1[02-9ac-hj-np-z]{7,87}$/;
const CASH_ADDR_WITH_PREFIX = /^bitcoincash:[02-9ac-hj-np-z]{42,}$/;
const CASH_ADDR_WITHOUT_PREFIX = /^[pq][02-9ac-hj-np-z]{41,}$/;
const SIXTY_FOUR_HEX_CHARS = /^[\dA-Fa-f]{64}$/;

export function isValidBtcAddress(address?: string): boolean {
  if (!address)
    return false;

  return P2PKH_OR_P2SH.test(address) || BECH32.test(address);
}

export function isValidBchAddress(address?: string): boolean {
  if (!address)
    return false;

  return P2PKH_OR_P2SH.test(address)
    || CASH_ADDR_WITH_PREFIX.test(address)
    || CASH_ADDR_WITHOUT_PREFIX.test(address);
}

const BASE58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz';
const BASE58_BASE = 58;

function createBase58Map(alphabet: string): Uint8Array {
  const map = new Uint8Array(256).fill(255);
  for (let i = 0; i < alphabet.length; i++)
    map[alphabet.charCodeAt(i)] = i;
  return map;
}

function countLeadingChars(str: string, leader: string): number {
  let count = 0;
  while (str[count] === leader)
    count++;
  return count;
}

/**
 * Copies the significant tail of the scratch buffer out, re-attaching the leading zero bytes.
 *
 * @remarks
 * The scratch buffer is over-allocated and right-aligned, so its head is padding that must be
 * skipped, while the zero bytes the encoding dropped have to be restored in front.
 * @param b256 - the over-allocated big-endian scratch buffer written by the decode loop
 * @param length - how many bytes at the tail of `b256` the loop actually touched
 * @param zeroes - how many zero bytes to prepend, one per leading '1' in the input
 */
function buildDecodedResult(b256: Uint8Array, length: number, zeroes: number): Uint8Array {
  const size = b256.length;
  let it = size - length;
  while (it !== size && b256[it] === 0)
    it++;
  const vch = new Uint8Array(zeroes + (size - it));
  let j = zeroes;
  while (it !== size)
    vch[j++] = b256[it++];
  return vch;
}

/**
 * Converts a base58 string into the big-endian bytes it encodes, leading zero bytes included.
 *
 * @remarks
 * Rejects rather than tolerates: every caller here treats a throw as "not a valid address", so
 * malformed input must never come back as a short or empty buffer.
 * @throws Error when a character is outside the base58 alphabet, or the carry does not clear.
 * @see https://github.com/cryptocoinjs/base-x/blob/master/src/esm/index.js
 */
function decodeBase58(str: string): Uint8Array {
  if (str.length === 0)
    return new Uint8Array();

  const BASE_MAP = createBase58Map(BASE58_ALPHABET);
  const FACTOR = Math.log(BASE58_BASE) / Math.log(256);

  const zeroes = countLeadingChars(str, BASE58_ALPHABET.charAt(0));
  let psz = zeroes;
  let length = 0;

  const size = (((str.length - psz) * FACTOR) + 1) >>> 0;
  const b256 = new Uint8Array(size);

  while (psz < str.length) {
    const charCode = str.charCodeAt(psz);

    if (charCode > BASE_MAP.length - 1)
      throw new Error('Invalid character');

    let carry = BASE_MAP[charCode];

    if (carry === 255)
      throw new Error('Invalid character');

    let i = 0;
    for (let it = size - 1; (carry !== 0 || i < length) && (it !== -1); it--, i++) {
      carry += (BASE58_BASE * b256[it]) >>> 0;
      b256[it] = (carry % 256) >>> 0;
      carry = (carry / 256) >>> 0;
    }

    if (carry !== 0)
      throw new Error('Non-zero carry');

    length = i;
    psz++;
  }

  return buildDecodedResult(b256, length, zeroes);
}

export function isValidSolanaAddress(address?: string): boolean {
  if (!address || address.length < 32 || address.length > 44)
    return false;

  try {
    const decoded = decodeBase58(address);
    return decoded.length === 32;
  }
  catch {
    return false;
  }
}

/** Network prefix bytes of the two substrate networks rotki accepts: Polkadot and Kusama. */
const SS58_PREFIXES = new Set<number>([0, 2]);
/** One prefix byte, a 32-byte public key, and a two-byte checksum. */
const SS58_DECODED_LENGTH = 35;

/**
 * Whether the value is a Polkadot or Kusama address.
 *
 * The two-byte checksum is a blake2b digest, which is not verified here: the decoded length and
 * the network prefix already reject anything that is not an address, and the sibling validators
 * above check shape rather than checksums too. The authoritative check is the backend's
 * `check_chain_ecosystem`, which is what any surviving bad value is answered by.
 */
export function isValidSs58Address(address?: string): boolean {
  if (!address || address.length < 46 || address.length > 48)
    return false;

  try {
    const decoded = decodeBase58(address);
    return decoded.length === SS58_DECODED_LENGTH && SS58_PREFIXES.has(decoded[0]);
  }
  catch {
    return false;
  }
}

export function isValidAddress(address?: string): boolean {
  return isValidEthAddress(address)
    || isValidBtcAddress(address)
    || isValidBchAddress(address)
    || isValidSolanaAddress(address)
    || isValidSs58Address(address);
}

export function isValidEvmTxHash(address?: string): boolean {
  if (!address)
    return false;

  return /^0x[\dA-Fa-f]{64}$/.test(address);
}

export function isValidBtcTxHash(txHash?: string): boolean {
  if (!txHash)
    return false;

  return SIXTY_FOUR_HEX_CHARS.test(txHash);
}

export function isValidSolanaSignature(signature?: string): boolean {
  if (!signature || signature.length < 87 || signature.length > 88)
    return false;

  try {
    const decoded = decodeBase58(signature);
    return decoded.length === 64; // Solana signatures are 64 bytes
  }
  catch {
    return false;
  }
}

export function isValidTxHashOrSignature(txHash?: string): boolean {
  return isValidEvmTxHash(txHash) || isValidBtcTxHash(txHash) || isValidSolanaSignature(txHash);
}
