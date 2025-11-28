import {
  consistOfNumbers,
  decodeHtmlEntities,
  getTextToken,
  isValidAddress,
  isValidBchAddress,
  isValidBtcAddress,
  isValidBtcTxHash,
  isValidEthAddress,
  isValidEvmTxHash,
  isValidSolanaAddress,
  isValidSolanaSignature,
  isValidTxHashOrSignature,
  isValidUrl,
  toCapitalCase,
  toHumanReadable,
  toSentenceCase,
  toSnakeCase,
  transformCase,
} from '@rotki/common';
import { describe, expect, it } from 'vitest';

describe('utils/text', () => {
  it('check return value of human readable function', () => {
    expect(toHumanReadable('lorem_ipsum dolor sit_amet')).toEqual('lorem ipsum dolor sit amet');
    expect(toHumanReadable('polygon_pos')).toEqual('polygon pos');
    expect(toHumanReadable('polygon_pos', 'uppercase')).toEqual('POLYGON POS');
    expect(toHumanReadable('polygon_pos', 'capitalize')).toEqual('Polygon Pos');
    expect(toHumanReadable('polygon_POS', 'capitalize')).toEqual('Polygon POS');
    expect(toHumanReadable('polygon_pos', 'sentence')).toEqual('Polygon pos');
    expect(toHumanReadable('POLYGON_POS', 'sentence')).toEqual('POLYGON POS');
    expect(toHumanReadable('polygon_pos', 'lowercase')).toEqual('polygon pos');
    expect(toHumanReadable('POLYGON_POS', 'lowercase')).toEqual('polygon pos');
    expect(toHumanReadable('POLYGON_pos', 'lowercase')).toEqual('polygon pos');
  });

  it('check return value of transform case function', () => {
    expect(transformCase('lorem_ipsum_dolor_sit_amet', true)).toEqual('loremIpsumDolorSitAmet');
    expect(transformCase('lorem_ipsum_dolor_sit_amet')).toEqual('lorem_ipsum_dolor_sit_amet');
    expect(transformCase('loremIpsumDolorSitAmet')).toEqual('lorem_ipsum_dolor_sit_amet');
    expect(transformCase('loremIpsumDolorSitAmet', true)).toEqual('loremIpsumDolorSitAmet');
  });

  it('check return value of toSentenceCase function', () => {
    expect(toSentenceCase('this is a sentence')).toEqual('This is a sentence');
    expect(toSentenceCase('HELLO WORLD')).toEqual('HELLO WORLD');
    expect(toSentenceCase('hello')).toEqual('Hello');
    expect(toSentenceCase('h')).toEqual('H');
    expect(toSentenceCase('')).toEqual('');
    expect(toSentenceCase('123 numbers')).toEqual('123 numbers');
  });

  it('check return value of getTextToken function', () => {
    expect(getTextToken('this is a sentence')).toEqual('thisisasentence');
    expect(getTextToken('Hello World!')).toEqual('helloworld');
    expect(getTextToken('Test-123_abc')).toEqual('test123abc');
    expect(getTextToken('  SPACED  ')).toEqual('spaced');
    expect(getTextToken('special!@#$%^&*()chars')).toEqual('specialchars');
    expect(getTextToken('')).toEqual('');
    expect(getTextToken('123abc456')).toEqual('123abc456');
  });

  it('check return value of toSnakeCase function', () => {
    expect(toSnakeCase('thisIsAString')).toEqual('this_is_a_string');
    expect(toSnakeCase('ThisIsAString')).toEqual('this_is_a_string');
    expect(toSnakeCase('this is a sentence')).toEqual('this_is_a_sentence');
    expect(toSnakeCase('CONSTANT_CASE')).toEqual('c_o_n_s_t_a_n_t__c_a_s_e');
    expect(toSnakeCase('mixedCase123')).toEqual('mixed_case123');
    expect(toSnakeCase('')).toEqual('');
    expect(toSnakeCase('already_snake_case')).toEqual('already_snake_case');
  });

  it('check return value of toCapitalCase function', () => {
    expect(toCapitalCase('this is a sentence')).toEqual('This Is A Sentence');
    expect(toCapitalCase('hello world')).toEqual('Hello World');
    expect(toCapitalCase('it\'s a test')).toEqual('It\'s A Test');
    expect(toCapitalCase('ALREADY CAPS')).toEqual('ALREADY CAPS');
    expect(toCapitalCase('mixed CASE text')).toEqual('Mixed CASE Text');
    expect(toCapitalCase('123 numbers here')).toEqual('123 Numbers Here');
    expect(toCapitalCase('')).toEqual('');
  });

  it('check validation of Ethereum addresses', () => {
    // Valid addresses
    expect(isValidEthAddress('0x742d35Cc6634C0532925a3b844Bc9e7595f0bEbB')).toBe(true);
    expect(isValidEthAddress('0x0000000000000000000000000000000000000000')).toBe(true);
    expect(isValidEthAddress('0xFFfFfFffFFfffFFfFFfFFFFFffFFFffffFfFFFfF')).toBe(true);
    expect(isValidEthAddress('0x1234567890123456789012345678901234567890')).toBe(true);

    // Invalid addresses
    expect(isValidEthAddress('')).toBe(false);
    expect(isValidEthAddress(undefined)).toBe(false);
    expect(isValidEthAddress('0x')).toBe(false);
    expect(isValidEthAddress('0x123')).toBe(false);
    expect(isValidEthAddress('0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb')).toBe(false); // Missing one character
    expect(isValidEthAddress('742d35Cc6634C0532925a3b844Bc9e7595f0bEbB')).toBe(false); // Missing 0x
    expect(isValidEthAddress('0x742d35Cc6634C0532925a3b844Bc9e7595f0bEbBG')).toBe(false); // Invalid hex char
    expect(isValidEthAddress('0x742d35Cc6634C0532925a3b844Bc9e7595f0bEbB0')).toBe(false); // Too long
  });

  it('check validation of Bitcoin addresses', () => {
    // Valid P2PKH addresses (start with 1)
    expect(isValidBtcAddress('1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa')).toBe(true);
    expect(isValidBtcAddress('1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2')).toBe(true);

    // Valid P2SH addresses (start with 3)
    expect(isValidBtcAddress('3J98t1WpEZ73CNmYviecrnyiWrnqRhWNLy')).toBe(true);
    expect(isValidBtcAddress('3QJmV3qfvL9SuYo34YihAf3sRCW3qSinyC')).toBe(true);

    // Valid Bech32 addresses (start with bc1)
    expect(isValidBtcAddress('bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4')).toBe(true);
    expect(isValidBtcAddress('bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq')).toBe(true);

    // Invalid addresses
    expect(isValidBtcAddress('')).toBe(false);
    expect(isValidBtcAddress(undefined)).toBe(false);
    expect(isValidBtcAddress('0A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa')).toBe(false); // Invalid first char
    expect(isValidBtcAddress('1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfO')).toBe(false); // Contains O
    expect(isValidBtcAddress('bc2qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4')).toBe(false); // Invalid prefix
  });

  it('check validation of Bitcoin Cash addresses', () => {
    // Valid legacy format (same as Bitcoin)
    expect(isValidBchAddress('1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa')).toBe(true);
    expect(isValidBchAddress('3J98t1WpEZ73CNmYviecrnyiWrnqRhWNLy')).toBe(true);

    // Valid CashAddr format with prefix
    expect(isValidBchAddress('bitcoincash:qpm2qsznhks23z7629mms6s4cwef74vcwvy22gdx6a')).toBe(true);
    expect(isValidBchAddress('bitcoincash:qr95sy3j9xwd2ap32xkykttr4cvcu7as4y0qverfuy')).toBe(true);

    // Valid CashAddr format without prefix
    expect(isValidBchAddress('qpm2qsznhks23z7629mms6s4cwef74vcwvy22gdx6a')).toBe(true);
    expect(isValidBchAddress('qr95sy3j9xwd2ap32xkykttr4cvcu7as4y0qverfuy')).toBe(true);

    // Invalid addresses
    expect(isValidBchAddress('')).toBe(false);
    expect(isValidBchAddress(undefined)).toBe(false);
    expect(isValidBchAddress('bitcoincash:')).toBe(false);
    expect(isValidBchAddress('bitcoin:qpm2qsznhks23z7629mms6s4cwef74vcwvy22gdx6a')).toBe(false); // Wrong prefix
  });

  it('check validation of Solana addresses', () => {
    // Valid Solana addresses (base58 encoded, 32-44 characters)
    expect(isValidSolanaAddress('7EqQdEULxWcraVx3mXKFjc84LhCkMGZCkRuDpvcMwJeK')).toBe(true);
    expect(isValidSolanaAddress('DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5CNSKK')).toBe(true);
    expect(isValidSolanaAddress('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA')).toBe(true);

    // Invalid addresses
    expect(isValidSolanaAddress('')).toBe(false);
    expect(isValidSolanaAddress(undefined)).toBe(false);
    expect(isValidSolanaAddress('999999999999999999999999999999999999')).toBe(false);
    expect(isValidSolanaAddress('tooshort')).toBe(false);
    expect(isValidSolanaAddress('7EqQdEULxWcraVx3mXKFjc84LhCkMGZCkRuDpvcMwJeK0')).toBe(false); // Invalid character
    expect(isValidSolanaAddress('InvalidBase58WithOandI')).toBe(false); // Contains invalid base58 chars
  });

  it('check validation of generic addresses', () => {
    // Should return true for any valid address type
    expect(isValidAddress('0x742d35Cc6634C0532925a3b844Bc9e7595f0bEbB')).toBe(true); // ETH
    expect(isValidAddress('1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa')).toBe(true); // BTC
    expect(isValidAddress('qpm2qsznhks23z7629mms6s4cwef74vcwvy22gdx6a')).toBe(true); // BCH
    expect(isValidAddress('7EqQdEULxWcraVx3mXKFjc84LhCkMGZCkRuDpvcMwJeK')).toBe(true); // SOL

    // Invalid
    expect(isValidAddress('invalid-address')).toBe(false);
    expect(isValidAddress('')).toBe(false);
    expect(isValidAddress(undefined)).toBe(false);
  });

  it('check validation of EVM transaction hashes', () => {
    // Valid EVM tx hashes (0x followed by 64 hex characters)
    expect(isValidEvmTxHash('0x5c504ed432cb51138bcf09aa5e8a410dd4a1e204ef84bfed1be16dfba1b22060')).toBe(true);
    expect(isValidEvmTxHash('0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef')).toBe(true);
    expect(isValidEvmTxHash('0xABCDEF1234567890ABCDEF1234567890ABCDEF1234567890ABCDEF1234567890')).toBe(true);

    // Invalid hashes
    expect(isValidEvmTxHash('')).toBe(false);
    expect(isValidEvmTxHash(undefined)).toBe(false);
    expect(isValidEvmTxHash('0x')).toBe(false);
    expect(isValidEvmTxHash('0x5c504ed432cb51138bcf09aa5e8a410dd4a1e204ef84bfed1be16dfba1b2206')).toBe(false); // Too short
    expect(isValidEvmTxHash('5c504ed432cb51138bcf09aa5e8a410dd4a1e204ef84bfed1be16dfba1b22060')).toBe(false); // Missing 0x
    expect(isValidEvmTxHash('0x5c504ed432cb51138bcf09aa5e8a410dd4a1e204ef84bfed1be16dfba1b22060G')).toBe(false); // Invalid hex
  });

  it('check validation of Bitcoin transaction hashes', () => {
    // Valid BTC tx hashes (64 hex characters, no 0x prefix)
    expect(isValidBtcTxHash('5c504ed432cb51138bcf09aa5e8a410dd4a1e204ef84bfed1be16dfba1b22060')).toBe(true);
    expect(isValidBtcTxHash('1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef')).toBe(true);
    expect(isValidBtcTxHash('ABCDEF1234567890ABCDEF1234567890ABCDEF1234567890ABCDEF1234567890')).toBe(true);

    // Invalid hashes
    expect(isValidBtcTxHash('')).toBe(false);
    expect(isValidBtcTxHash(undefined)).toBe(false);
    expect(isValidBtcTxHash('5c504ed432cb51138bcf09aa5e8a410dd4a1e204ef84bfed1be16dfba1b2206')).toBe(false); // Too short
    expect(isValidBtcTxHash('0x5c504ed432cb51138bcf09aa5e8a410dd4a1e204ef84bfed1be16dfba1b22060')).toBe(false); // Has 0x
    expect(isValidBtcTxHash('5c504ed432cb51138bcf09aa5e8a410dd4a1e204ef84bfed1be16dfba1b22060G')).toBe(false); // Invalid hex
  });

  it('check validation of Solana signatures', () => {
    // Valid Solana signatures (base58, 87-88 characters, decodes to 64 bytes)
    expect(isValidSolanaSignature('5VERv8NMvzbJMEkV8xnrLkEaWRtSz9CosKDYjCJjBRnbJLgp8uirBgmQpjKhoR4tjF3ZpRzrFmBV6UjKdiSZkQUW')).toBe(true);
    expect(isValidSolanaSignature('3nGJm9dqGhfyJzkLhL7KMQqGGQqyL5aLqWJNF8JvqSDqWqCRAkVVdDhTZmTHJHVQtDk3LLwYvBSVCH9Tg4CKnWqA')).toBe(true);

    // Invalid signatures
    expect(isValidSolanaSignature('')).toBe(false);
    expect(isValidSolanaSignature(undefined)).toBe(false);
    expect(isValidSolanaSignature('tooshort')).toBe(false);
    expect(isValidSolanaSignature('5VERv8NMvzbJMEkV8xnrLkEaWRtSz9CosKDYjCJjBRnbJLgp8uirBgmQpjKhoR4tjF3ZpRzrFmBV6UjKdiSZkQUW0')).toBe(false); // Invalid character '0'
    expect(isValidSolanaSignature('999999999999999999999999999999999999999999999999999999999999999999999999999999999999999')).toBe(true); // Valid base58 encoding that decodes to 64 bytes
  });

  it('check validation of transaction hashes or signatures', () => {
    // Valid EVM
    expect(isValidTxHashOrSignature('0x5c504ed432cb51138bcf09aa5e8a410dd4a1e204ef84bfed1be16dfba1b22060')).toBe(true);

    // Valid BTC
    expect(isValidTxHashOrSignature('5c504ed432cb51138bcf09aa5e8a410dd4a1e204ef84bfed1be16dfba1b22060')).toBe(true);

    // Valid Solana
    expect(isValidTxHashOrSignature('5VERv8NMvzbJMEkV8xnrLkEaWRtSz9CosKDYjCJjBRnbJLgp8uirBgmQpjKhoR4tjF3ZpRzrFmBV6UjKdiSZkQUW')).toBe(true);

    // Invalid
    expect(isValidTxHashOrSignature('invalid-hash')).toBe(false);
    expect(isValidTxHashOrSignature('')).toBe(false);
    expect(isValidTxHashOrSignature(undefined)).toBe(false);
  });

  it('check if text consists of numbers only', () => {
    expect(consistOfNumbers('123')).toBe(true);
    expect(consistOfNumbers('0')).toBe(true);
    expect(consistOfNumbers('999999')).toBe(true);
    expect(consistOfNumbers('12345678901234567890')).toBe(true);

    expect(consistOfNumbers('123abc')).toBe(false);
    expect(consistOfNumbers('abc')).toBe(false);
    expect(consistOfNumbers('12.34')).toBe(false);
    expect(consistOfNumbers('12,34')).toBe(false);
    expect(consistOfNumbers('12 34')).toBe(false);
    expect(consistOfNumbers('-123')).toBe(false);
    expect(consistOfNumbers('+123')).toBe(false);
    expect(consistOfNumbers('')).toBe(false);
    expect(consistOfNumbers(undefined)).toBe(false);
  });

  it('check validation of URLs', () => {
    // Valid URLs
    expect(isValidUrl('https://example.com')).toBe(true);
    expect(isValidUrl('http://example.com')).toBe(true);
    expect(isValidUrl('https://www.example.com')).toBe(true);
    expect(isValidUrl('https://example.com/path/to/page')).toBe(true);
    expect(isValidUrl('https://example.com/path?query=value')).toBe(true);
    expect(isValidUrl('https://example.com:8080')).toBe(true);
    expect(isValidUrl('https://sub.example.com')).toBe(true);
    expect(isValidUrl('https://example.com/path#anchor')).toBe(true);
    expect(isValidUrl('https://example.com/path?q=1&p=2')).toBe(true);

    // Invalid URLs
    expect(isValidUrl('')).toBe(false);
    expect(isValidUrl(undefined)).toBe(false);
    expect(isValidUrl('example.com')).toBe(false); // Missing protocol
    expect(isValidUrl('ftp://example.com')).toBe(false); // Wrong protocol
    expect(isValidUrl('https://')).toBe(false);
    expect(isValidUrl('https://example')).toBe(false);
    expect(isValidUrl('not a url')).toBe(false);
  });

  it('check decoding of HTML entities', () => {
    // Note: Using numeric entity &#8226; instead of &bull; because happy-dom
    // doesn't support all named HTML entities (only basic ones like &lt; &gt; &amp;)
    expect(decodeHtmlEntities('&#8226;')).toEqual('•');
    expect(decodeHtmlEntities('&lt;div&gt;')).toEqual('<div>');
    expect(decodeHtmlEntities('&amp;')).toEqual('&');
    expect(decodeHtmlEntities('&quot;')).toEqual('"');
    expect(decodeHtmlEntities('&apos;')).toEqual('\'');
    expect(decodeHtmlEntities('&#169;')).toEqual('©');
    expect(decodeHtmlEntities('&#x2665;')).toEqual('♥');
    expect(decodeHtmlEntities('Hello &amp; welcome &lt;test&gt;')).toEqual('Hello & welcome <test>');
    expect(decodeHtmlEntities('plain text')).toEqual('plain text');
    expect(decodeHtmlEntities('')).toEqual('');
  });
});
