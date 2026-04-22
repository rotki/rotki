import { describe, expect, it } from 'vitest';
import { XpubKeyType } from '@/modules/accounts/blockchain-accounts';
import { detectXpubType, getKeyType, getPrefix, guessPrefix, isBtcAddress, isPrefixed, XpubPrefix } from './xpub';

describe('detectXpubType', () => {
  it('returns null for empty string', () => {
    expect(detectXpubType('')).toBeNull();
  });

  it('returns null for whitespace-only string', () => {
    expect(detectXpubType('   ')).toBeNull();
  });

  it('returns null for random text', () => {
    expect(detectXpubType('hello world')).toBeNull();
  });

  it('detects ypub as YPUB', () => {
    expect(detectXpubType('ypub6Ww3ibxVfGzLrAH1PNcjyAWPKPPjLzQ7T9Mmfa18oF5dKaPSLDB6FghfZ1XxjVCGX2j4YMEsBX4M7Krjq6iHHJE97J7MkLgv6QC8MWKDXBL')).toBe(XpubPrefix.YPUB);
  });

  it('detects zpub as ZPUB', () => {
    expect(detectXpubType('zpub6rFR7y4Q2AijBEqTUqyzEyyxJewTSzAoot2vTBgN9r2fUKFJFfQwMiJZ2mq5YEZb6jhLjPtqyRUFHCBs7WkBCCesb5KMRE9T4cFT2UPyBYF')).toBe(XpubPrefix.ZPUB);
  });

  it('returns ambiguous for xpub prefix', () => {
    expect(detectXpubType('xpub6CUGRUonZSQ4TWtTMmzXdrXDtyPWKiMJ7abWaX2ZFGvV3Gg7FbqXdRxivu1nQFCWEPa4UUgJGPkExPNm5')).toBe('ambiguous');
  });

  it('returns address for BTC addresses', () => {
    expect(detectXpubType('1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa')).toBe('address');
    expect(detectXpubType('bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq')).toBe('address');
  });

  it('returns address for BCH CashAddr addresses', () => {
    expect(detectXpubType('bitcoincash:qpm2qsznhks23z7629mms6s4cwef74vcwvy22gdx6a')).toBe('address');
  });

  it('trims whitespace before detection', () => {
    expect(detectXpubType('  zpub6rFR7y4Q2AijBEqTUqyzEyyxJewTSzAoot2vTBgN9r2fUKFJFfQwMiJZ2mq5YEZb6jhLjPtqyRUFHCBs7WkBCCesb5KMRE9T4cFT2UPyBYF  ')).toBe(XpubPrefix.ZPUB);
  });
});

describe('isPrefixed', () => {
  it('matches xpub prefixed strings', () => {
    const result = isPrefixed('xpub123');
    expect(result).toBeTruthy();
    expect(result?.[1]).toBe('xpub');
  });

  it('matches ypub prefixed strings', () => {
    const result = isPrefixed('ypub456');
    expect(result).toBeTruthy();
    expect(result?.[1]).toBe('ypub');
  });

  it('matches zpub prefixed strings', () => {
    const result = isPrefixed('zpub789');
    expect(result).toBeTruthy();
    expect(result?.[1]).toBe('zpub');
  });

  it('returns null for non-prefixed strings', () => {
    expect(isPrefixed('abc123')).toBeNull();
  });

  it('returns null for empty string', () => {
    expect(isPrefixed('')).toBeNull();
  });
});

describe('getKeyType', () => {
  it('maps XPUB prefix to XPUB key type', () => {
    expect(getKeyType(XpubPrefix.XPUB)).toBe(XpubKeyType.XPUB);
  });

  it('maps YPUB prefix to YPUB key type', () => {
    expect(getKeyType(XpubPrefix.YPUB)).toBe(XpubKeyType.YPUB);
  });

  it('maps ZPUB prefix to ZPUB key type', () => {
    expect(getKeyType(XpubPrefix.ZPUB)).toBe(XpubKeyType.ZPUB);
  });

  it('maps P2TR prefix to P2TR key type', () => {
    expect(getKeyType(XpubPrefix.P2TR)).toBe(XpubKeyType.P2TR);
  });
});

describe('getPrefix', () => {
  it('returns YPUB for YPUB key type', () => {
    expect(getPrefix(XpubKeyType.YPUB)).toBe(XpubPrefix.YPUB);
  });

  it('returns ZPUB for ZPUB key type', () => {
    expect(getPrefix(XpubKeyType.ZPUB)).toBe(XpubPrefix.ZPUB);
  });

  it('returns P2TR for P2TR key type', () => {
    expect(getPrefix(XpubKeyType.P2TR)).toBe(XpubPrefix.P2TR);
  });

  it('returns XPUB as default', () => {
    expect(getPrefix()).toBe(XpubPrefix.XPUB);
    expect(getPrefix(XpubKeyType.XPUB)).toBe(XpubPrefix.XPUB);
  });
});

describe('guessPrefix', () => {
  it('guesses xpub prefix', () => {
    expect(guessPrefix('xpub123')).toBe(XpubPrefix.XPUB);
  });

  it('guesses ypub prefix', () => {
    expect(guessPrefix('ypub456')).toBe(XpubPrefix.YPUB);
  });

  it('guesses zpub prefix', () => {
    expect(guessPrefix('zpub789')).toBe(XpubPrefix.ZPUB);
  });

  it('throws for non-prefixed string', () => {
    expect(() => guessPrefix('abc123')).toThrow('Invalid key');
  });
});

describe('isBtcAddress', () => {
  it('returns true for P2PKH address (starts with 1)', () => {
    expect(isBtcAddress('1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa')).toBe(true);
  });

  it('returns true for P2SH address (starts with 3)', () => {
    expect(isBtcAddress('3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy')).toBe(true);
  });

  it('returns true for bech32 SegWit address (bc1q)', () => {
    expect(isBtcAddress('bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq')).toBe(true);
  });

  it('returns true for Taproot address (bc1p)', () => {
    expect(isBtcAddress('bc1pmfr3p9j00pfxjh0zmgp99y8zftmd3s5pmedqhyptwy6lm87hf5sspknck9')).toBe(true);
  });

  it('returns true for BCH CashAddr address', () => {
    expect(isBtcAddress('bitcoincash:qpm2qsznhks23z7629mms6s4cwef74vcwvy22gdx6a')).toBe(true);
  });

  it('returns false for empty string', () => {
    expect(isBtcAddress('')).toBe(false);
  });

  it('returns false for whitespace-only string', () => {
    expect(isBtcAddress('   ')).toBe(false);
  });

  it('returns false for xpub strings', () => {
    expect(isBtcAddress('xpub6CUGRUonZSQ4TWtTMmzXdrXDtyPWKiMJ7abWaX2ZFGvV3Gg7FbqXdRxivu1nQFCWEPa4UUgJGPkExPNm5')).toBe(false);
  });

  it('returns false for random text', () => {
    expect(isBtcAddress('hello world')).toBe(false);
  });
});
