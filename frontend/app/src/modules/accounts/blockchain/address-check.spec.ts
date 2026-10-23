import { Blockchain } from '@rotki/common';
import { assert, describe, expect, it } from 'vitest';
import { type AddressCheck, addressCheckFor, AddressVerdict } from '@/modules/accounts/blockchain/address-check';

/**
 * Every expected verdict here is the backend's own answer for that entry, read from its validators
 * (`api/v1/schemas.py`); the addresses were made with its encoders. A typo changes one character.
 */
function checkFor(chain: string, takesHex = false): AddressCheck {
  const check = addressCheckFor(chain, takesHex);
  assert(check);
  return check;
}

const { ADDRESS, INVALID, NAME } = AddressVerdict;

describe('addressCheckFor', () => {
  describe('hex chains', () => {
    const check = checkFor(Blockchain.ETH, true);

    it.each([
      ['a checksummed address', '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c', ADDRESS],
      ['an address with a wrong checksum', '0x5a0B54D5dc17e0AadC383d2db43B0a0D3E029c4c', ADDRESS],
      ['an address without its 0x', '5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c', ADDRESS],
      ['an address one digit short', '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4', INVALID],
      ['an ENS name', 'rotki.eth', NAME],
      ['a DNS name under ENS', 'sub.rotki.box', NAME],
      ['a name typed with an ideographic dot', 'rotki。eth', NAME],
      ['a top-level domain one character long', 'rotki.e', INVALID],
      ['a name with an empty label', 'rotki..eth', INVALID],
      ['a bare word', 'vitalik', INVALID],
    ])('should judge %s', (_, entry, verdict) => {
      expect(check(entry)).toBe(verdict);
    });
  });

  describe('bitcoin', () => {
    const check = checkFor(Blockchain.BTC);

    it.each([
      ['a P2PKH address', '1ARd3SagYkcyZvCphh6S1mfTxRvGwUN279', ADDRESS],
      ['a P2PKH address with a typo', '1ARd3SagYkcyZvCph26S1mfTxRvGwUN279', INVALID],
      ['a P2SH address with a typo', '3D71zJS6rWNEm4Tq9224a1tL2r1kzGhwMr', INVALID],
      ['a segwit v0 address', 'bc1qmxg4v90jk7r6m3sk0pgxwzjy3cqkcdzu66738s', ADDRESS],
      ['a segwit v0 address in upper case', 'BC1QMXG4V90JK7R6M3SK0PGXWZJY3CQKCDZU66738S', ADDRESS],
      ['a segwit address in mixed case', 'bc1qmxg4v90jk7r6m3sk0pgxwzjy3cqkcdzu66738S', INVALID],
      ['a segwit v0 address with a typo', 'bc1qmxg4v90jk7r6m3sk02gxwzjy3cqkcdzu66738s', INVALID],
      ['a taproot address', 'bc1plhhgs9rksnnr9xmklgx4kgfh704mw2dlefce3m8m9hccp2fdpywqwes4hr', ADDRESS],
      ['a taproot address with a typo', 'bc1plhhgs9rksnnr9xmklgx4kgfh7042w2dlefce3m8m9hccp2fdpywqwes4hr', INVALID],
      ['a v1 address with a BIP-173 checksum', 'bc1pq54hnt73dv2w7m9pzcjyl8spv92z9pt8x0nvn7gw5vm8zsvtvlfs9dp7uh', ADDRESS],
      ['a dogecoin address', 'D7xG9VccM5kgayh5UE4fT559TXQ1s7TLUN', INVALID],
      ['an ENS name', 'rotki.eth', NAME],
    ])('should judge %s', (_, entry, verdict) => {
      expect(check(entry)).toBe(verdict);
    });
  });

  describe('bitcoin cash', () => {
    const check = checkFor(Blockchain.BCH);

    it.each([
      ['a CashAddr with its prefix', 'bitcoincash:qrpjqkhsk9u7cr3phhwm0xw8hunfhurgrucdlcrxn2', ADDRESS],
      ['a CashAddr without its prefix', 'qrpjqkhsk9u7cr3phhwm0xw8hunfhurgrucdlcrxn2', ADDRESS],
      ['a CashAddr in upper case', 'BITCOINCASH:QRPJQKHSK9U7CR3PHHWM0XW8HUNFHURGRUCDLCRXN2', ADDRESS],
      ['a CashAddr with a typo', 'bitcoincash:qrpjqkhsk9u7cr32hhwm0xw8hunfhurgrucdlcrxn2', INVALID],
      ['a legacy address', '13CXKtgDzJum8HF8uaZDyvFs5tyFHMCpUn', ADDRESS],
      ['a legacy address with a typo', '13CXKtgDzJum8HF8u2ZDyvFs5tyFHMCpUn', INVALID],
      ['an ENS name ending in .eth', 'rotki.eth', NAME],
      ['a DNS name, which the backend takes only for .eth', 'rotki.box', INVALID],
    ])('should judge %s', (_, entry, verdict) => {
      expect(check(entry)).toBe(verdict);
    });
  });

  describe('dogecoin', () => {
    const check = checkFor(Blockchain.DOGE);

    it.each([
      ['a P2PKH address', 'D7xG9VccM5kgayh5UE4fT559TXQ1s7TLUN', ADDRESS],
      ['a P2SH address', 'A1mdV77q8t57KYzL4igMshPfKT9wtezx4L', ADDRESS],
      ['an address with a typo', 'D7xG9VccM5kgayh5U24fT559TXQ1s7TLUN', INVALID],
      ['a bitcoin address', '1ARd3SagYkcyZvCphh6S1mfTxRvGwUN279', INVALID],
      ['an ENS name, which dogecoin does not take', 'rotki.eth', INVALID],
    ])('should judge %s', (_, entry, verdict) => {
      expect(check(entry)).toBe(verdict);
    });
  });

  describe('solana', () => {
    const check = checkFor(Blockchain.SOLANA);

    it.each([
      ['an address', 'CFn5Qo1k86PBDy5yZ3g1aJgdqc8ovAB4A8FFmqSgN7mc', ADDRESS],
      ['an address with a typo, which carries no checksum to catch it', 'CFn5Qo1k86PBDy5yZ3g1aJ2dqc8ovAB4A8FFmqSgN7mc', ADDRESS],
      ['31 bytes', '4Yno6LTYHMZea8xFA7t4Bp7nkg1zKL4ZufXnbYhpHXm', INVALID],
      ['a character outside base58', 'CFn5Qo1k86PBDy5yZ3g1aJgdqc8ovAB4A8FFmqSgN7m0', INVALID],
      ['an ENS name, which solana does not take', 'rotki.eth', INVALID],
    ])('should judge %s', (_, entry, verdict) => {
      expect(check(entry)).toBe(verdict);
    });
  });

  describe('substrate', () => {
    const polkadot = checkFor(Blockchain.DOT);
    const kusama = checkFor(Blockchain.KSM);

    it.each([
      ['a polkadot address on polkadot', polkadot, '127kGD26EeuB97RwHJ8gn5QrKnHDBamVMogo5Z2iChqcktqM', ADDRESS],
      ['a polkadot address with a typo', polkadot, '127kGD26EeuB97RwHJ8gn5Qr2nHDBamVMogo5Z2iChqcktqM', INVALID],
      ['a kusama address on polkadot', polkadot, 'GP7rzxjqNJvpxiSSUQX9WB6RkoNjFk1sCVwHMCssidC8jnf', INVALID],
      ['a kusama address on kusama', kusama, 'GP7rzxjqNJvpxiSSUQX9WB6RkoNjFk1sCVwHMCssidC8jnf', ADDRESS],
      ['a kusama address with a typo', kusama, 'GP7rzxjqNJvpxiSSUQX9WB62koNjFk1sCVwHMCssidC8jnf', INVALID],
      ['a public key, which the backend refuses', polkadot, `0x${'ab'.repeat(32)}`, INVALID],
      ['an ENS name', kusama, 'rotki.eth', NAME],
    ])('should judge %s', (_, check, entry, verdict) => {
      expect(check(entry)).toBe(verdict);
    });
  });

  it('should have no check for a chain it cannot judge, leaving its entries to the backend', () => {
    expect(addressCheckFor(Blockchain.ETH2, false)).toBeUndefined();
  });
});
