import { describe, expect, it } from 'vitest';
import {
  acceptsSensitiveEdit,
  type ExchangeCapabilities,
  type ExchangeKeysContext,
  type ExchangeKeysFormState,
  exchangeKeysSchema,
  historyLimitMessage,
  isBinance,
  isCoinbase,
  isEditing,
  isGate,
  isKraken,
  isOkx,
  normalizeApiSecret,
  requiresApiSecret,
  requiresPassphrase,
  showsBinanceHistoryImport,
  showsKeyWaitingTimeWarning,
} from '@/modules/settings/api-keys/exchange/exchange-keys-form';

const capabilities: ExchangeCapabilities = {
  withoutApiSecret: ['bitpanda'],
  withPassphrase: ['kucoin', 'okx'],
};

describe('settings/api-keys/exchange/exchange-keys-form', () => {
  describe('identifying the exchange', () => {
    it.each([
      ['binance', true],
      ['binanceus', true],
      ['kraken', false],
      ['', false],
    ])('should read %s as binance: %s', (location, expected) => {
      expect(isBinance(location)).toBe(expected);
    });

    it.each([
      ['gate', isGate],
      ['kraken', isKraken],
      ['okx', isOkx],
      ['coinbase', isCoinbase],
    ])('should match %s only against itself', (location, predicate) => {
      expect(predicate(location)).toBe(true);
      expect(predicate('kucoin')).toBe(false);
    });

    // `coinbaseprime` is a separate exchange, and only plain coinbase mangles its secret.
    it('should not read coinbaseprime as coinbase', () => {
      expect(isCoinbase('coinbaseprime')).toBe(false);
    });
  });

  describe('the api secret', () => {
    it('should be required by an exchange that has one', () => {
      expect(requiresApiSecret('kucoin', capabilities)).toBe(true);
    });

    it('should not be required by an exchange that has none', () => {
      expect(requiresApiSecret('bitpanda', capabilities)).toBe(false);
    });

    // An empty list is what the store holds before the backend answers; treating every exchange as
    // needing a secret is the safe reading, since that is the common case.
    it('should be required while the capabilities are unknown', () => {
      expect(requiresApiSecret('bitpanda', { withoutApiSecret: [], withPassphrase: [] })).toBe(true);
    });

    it('should turn coinbase escaped newlines into real ones', () => {
      expect(normalizeApiSecret('coinbase', 'a\\nb')).toBe('a\nb');
    });

    it('should leave other exchange secrets untouched', () => {
      expect(normalizeApiSecret('kraken', 'a\\nb')).toBe('a\\nb');
    });
  });

  describe('the passphrase', () => {
    it('should be required by an exchange that uses one', () => {
      expect(requiresPassphrase('kucoin', capabilities)).toBe(true);
    });

    it('should not be required by an exchange that does not', () => {
      expect(requiresPassphrase('kraken', capabilities)).toBe(false);
    });
  });

  describe('the mode', () => {
    it('should read edit as editing', () => {
      expect(isEditing('edit')).toBe(true);
    });

    it('should read add as not editing', () => {
      expect(isEditing('add')).toBe(false);
    });

    it.each([
      ['add', false, true],
      ['add', true, true],
      ['edit', false, false],
      ['edit', true, true],
    ])('should accept a sensitive edit in %s mode while editing is %s: %s', (mode, editing, expected) => {
      expect(acceptsSensitiveEdit(mode, editing)).toBe(expected);
    });
  });

  describe('the conditional sections', () => {
    it('should offer the binance history import when adding', () => {
      expect(showsBinanceHistoryImport('binance', 'add')).toBe(true);
    });

    it('should not offer it when editing', () => {
      expect(showsBinanceHistoryImport('binance', 'edit')).toBe(false);
    });

    it('should not offer it for another exchange', () => {
      expect(showsBinanceHistoryImport('kraken', 'add')).toBe(false);
    });

    it.each(['kraken', 'coinbase', 'coinbaseprime'])('should warn about the key delay for %s', (location) => {
      expect(showsKeyWaitingTimeWarning(location)).toBe(true);
    });

    it('should not warn for an exchange whose keys work at once', () => {
      expect(showsKeyWaitingTimeWarning('kucoin')).toBe(false);
    });

    it.each(['bybit', 'htx', 'cryptocom'])('should carry a history limit message for %s', (location) => {
      expect(historyLimitMessage(location)).toBeDefined();
    });

    it('should carry none for an exchange with a full history', () => {
      expect(historyLimitMessage('kraken')).toBeUndefined();
    });
  });
});

describe('settings/api-keys/exchange/exchangeKeysSchema', () => {
  function context(overrides: Partial<ExchangeKeysContext> = {}): ExchangeKeysContext {
    return {
      capabilities,
      editingFutures: false,
      editingKeys: false,
      location: 'kucoin',
      mode: 'add',
      ...overrides,
    };
  }

  // The default location is kucoin, which the fixture marks as needing a passphrase, so a complete
  // form has to carry one.
  function state(overrides: Partial<ExchangeKeysFormState> = {}): ExchangeKeysFormState {
    return {
      apiKey: 'key',
      apiSecret: 'secret',
      name: 'Kucoin 1',
      passphrase: 'phrase',
      ...overrides,
    };
  }

  function errorsFor(
    contextOverrides: Partial<ExchangeKeysContext> = {},
    stateOverrides: Partial<ExchangeKeysFormState> = {},
  ): string[] {
    const result = exchangeKeysSchema(context(contextOverrides)).safeParse(state(stateOverrides));
    if (result.success)
      return [];

    return result.error.issues.map(issue => issue.path.join('.'));
  }

  describe('the sensitive fields', () => {
    it('should accept a complete form', () => {
      expect(errorsFor()).toStrictEqual([]);
    });

    it('should demand the api key', () => {
      expect(errorsFor({}, { apiKey: '' })).toStrictEqual(['apiKey']);
    });

    // vuelidate's required trims, so whitespace alone never counted as an answer.
    it('should not accept whitespace as an api key', () => {
      expect(errorsFor({}, { apiKey: '   ' })).toStrictEqual(['apiKey']);
    });

    it('should demand the secret only from an exchange that has one', () => {
      expect(errorsFor({ location: 'bitpanda' }, { apiSecret: '' })).toStrictEqual([]);
      expect(errorsFor({}, { apiSecret: '' })).toStrictEqual(['apiSecret']);
    });

    it('should demand the passphrase only from an exchange that uses one', () => {
      expect(errorsFor({}, { passphrase: '' })).toStrictEqual(['passphrase']);
      expect(errorsFor({ location: 'kraken' }, { passphrase: '' })).toStrictEqual([]);
    });

    it('should demand nothing sensitive while the saved pair stays masked', () => {
      expect(errorsFor(
        { mode: 'edit' },
        { apiKey: '', apiSecret: '', newName: 'Kucoin 1', passphrase: '' },
      )).toStrictEqual([]);
    });

    it('should demand them again once a replacement is started', () => {
      expect(errorsFor(
        { editingKeys: true, mode: 'edit' },
        { apiKey: '', apiSecret: '', newName: 'Kucoin 1', passphrase: '' },
      )).toStrictEqual(['apiKey', 'apiSecret', 'passphrase']);
    });
  });

  describe('the kraken futures pair', () => {
    const kraken = { location: 'kraken' };

    it('should accept neither', () => {
      expect(errorsFor(kraken)).toStrictEqual([]);
    });

    it('should accept both', () => {
      expect(errorsFor(kraken, {
        krakenFuturesApiKey: 'fkey',
        krakenFuturesApiSecret: 'fsecret',
      })).toStrictEqual([]);
    });

    it('should demand the secret when only the key is given', () => {
      expect(errorsFor(kraken, { krakenFuturesApiKey: 'fkey' }))
        .toStrictEqual(['krakenFuturesApiSecret']);
    });

    it('should demand the key when only the secret is given', () => {
      expect(errorsFor(kraken, { krakenFuturesApiSecret: 'fsecret' }))
        .toStrictEqual(['krakenFuturesApiKey']);
    });

    /**
     * The pair is read from one state, so clearing the half that caused the demand clears the
     * demand with it. Judging each field against whatever the other last held is what let an
     * invalid pair through in an earlier form.
     */
    it('should stop demanding once the other half is cleared again', () => {
      expect(errorsFor(kraken, { krakenFuturesApiKey: '', krakenFuturesApiSecret: '' }))
        .toStrictEqual([]);
    });
  });

  describe('the per exchange fields', () => {
    it('should demand the binance markets', () => {
      expect(errorsFor({ location: 'binance' }, { binanceHistoryStartTs: 1 }))
        .toStrictEqual(['binanceMarkets']);
    });

    it('should demand the binance start date when adding', () => {
      expect(errorsFor({ location: 'binance' }, { binanceMarkets: ['BTCUSDT'] }))
        .toStrictEqual(['binanceHistoryStartTs']);
    });

    it('should not demand the start date when editing', () => {
      expect(errorsFor(
        { location: 'binance', mode: 'edit' },
        { binanceMarkets: ['BTCUSDT'], newName: 'Binance 1' },
      )).toStrictEqual([]);
    });

    it('should demand the gate region', () => {
      expect(errorsFor({ location: 'gate' })).toStrictEqual(['gateLocation']);
    });

    it('should demand the okx region', () => {
      expect(errorsFor({ location: 'okx' }, { passphrase: 'phrase' })).toStrictEqual(['okxLocation']);
    });
  });

  describe('the name', () => {
    it('should be demanded when adding', () => {
      expect(errorsFor({}, { name: '' })).toStrictEqual(['name']);
    });

    it('should be ignored when editing, where the new name is demanded instead', () => {
      expect(errorsFor({ mode: 'edit' }, { name: '', newName: '' })).toStrictEqual(['newName']);
    });
  });
});
