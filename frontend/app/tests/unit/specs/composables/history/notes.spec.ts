import { bigNumberify, Blockchain, isEvmIdentifier } from '@rotki/common';
import { describe, expect, it, vi } from 'vitest';
import { type NoteFormat, NoteType, useHistoryEventNote } from '@/composables/history/events/notes';
import { useFrontendSettingsStore } from '@/store/settings/frontend';

vi.mock('@/composables/assets/retrieval', () => ({
  useAssetInfoRetrieval: vi.fn().mockReturnValue({
    assetSymbol: vi.fn().mockImplementation((identifier) => {
      if (isEvmIdentifier(identifier))
        return 'USDC';

      if (identifier === '0xdeadbeef')
        return '';

      return identifier;
    }),
  }),
}));

describe('composables::history/notes', () => {
  setActivePinia(createPinia());
  const { formatNotes } = useHistoryEventNote();
  const store = useFrontendSettingsStore();

  it('normal text', () => {
    const notes = 'Normal text';

    const formatted = get(formatNotes({ notes }));

    const expected: NoteFormat[] = [
      {
        type: NoteType.WORD,
        word: 'Normal text',
      },
    ];

    expect(formatted).toMatchObject(expected);
  });

  it('with amount and asset', () => {
    const notes = 'Receive 100 ETH';

    const formatted = get(formatNotes({ notes, amount: bigNumberify(100), assetId: 'ETH' }));

    const expected: NoteFormat[] = [
      {
        type: NoteType.WORD,
        word: 'Receive',
      },
      {
        type: NoteType.AMOUNT,
        amount: bigNumberify(100),
        asset: 'ETH',
      },
    ];

    expect(formatted).toMatchObject(expected);
  });

  it('with amount and asset (but formatted amount with thousand separator in the notes)', () => {
    const notes = 'Receive 15,123.233 ETH';
    const formatted = get(formatNotes({ notes, amount: bigNumberify(15123.233), assetId: 'ETH' }));

    const expected: NoteFormat[] = [
      {
        type: NoteType.WORD,
        word: 'Receive',
      },
      {
        type: NoteType.AMOUNT,
        amount: bigNumberify(15123.233),
        asset: 'ETH',
      },
    ];

    expect(formatted).toMatchObject(expected);
  });

  it('with amount and asset (but different asset symbol)', () => {
    const notes = 'Pay 100 EUR';

    const formatted = get(formatNotes({ notes, amount: bigNumberify(100), assetId: 'EURe' }));

    const expected: NoteFormat[] = [
      {
        type: NoteType.WORD,
        word: 'Pay',
      },
      {
        type: NoteType.AMOUNT,
        amount: bigNumberify(100),
      },
      {
        type: NoteType.WORD,
        word: 'EUR',
      },
    ];

    expect(formatted).toMatchObject(expected);
  });

  it('with amount and asset (multi-word)', () => {
    const notes = 'Receive 100 Spectral Token';

    const formatted = get(formatNotes({ notes, amount: bigNumberify(100), assetId: 'Spectral Token' }));

    const expected: NoteFormat[] = [
      {
        type: NoteType.WORD,
        word: 'Receive',
      },
      {
        type: NoteType.AMOUNT,
        amount: bigNumberify(100),
        asset: 'Spectral Token',
      },
    ];

    expect(formatted).toMatchObject(expected);
  });

  it('with ETH address', () => {
    const address = '0xCb2286d9471cc185281c4f763d34A962ED212962';
    const notes = `Address ${address}`;

    const formatted = get(formatNotes({ notes }));

    const expected: NoteFormat[] = [
      {
        type: NoteType.WORD,
        word: 'Address',
      },
      {
        type: NoteType.ADDRESS,
        address,
        showHashLink: true,
      },
    ];

    expect(formatted).toMatchObject(expected);
  });

  it('with multiple ETH addresses', () => {
    const address = '0xCb2286d9471cc185281c4f763d34A962ED212962';
    const notes = `Address ${address},${address}`;

    const formatted = get(formatNotes({ notes }));

    const expected: NoteFormat[] = [
      {
        type: NoteType.WORD,
        word: 'Address',
      },
      {
        type: NoteType.ADDRESS,
        address,
        showHashLink: true,
      },
      {
        type: NoteType.ADDRESS,
        address,
        showHashLink: true,
      },
    ];

    expect(formatted).toMatchObject(expected);
  });

  it('with BTC or BCH addresses', () => {
    const address1 = 'bc1qdf3av8da4up78shctfual6j6cv3kyvcw6qk3fz';
    const address2 = 'qz5hccuhr036drq7m3mah3qf5x3f5phv05v5rtu5z2';
    const rawAddress3 = 'qq0mjr27zmddcyclnsmuyj4cg5s846vtaycstug867';
    const address3 = `bitcoincash:${rawAddress3}`;
    const notes = `Address ${address1},${address2},${address3}`;

    const formatted = get(formatNotes({ notes }));

    const expected: NoteFormat[] = [
      {
        type: NoteType.WORD,
        word: 'Address',
      },
      {
        type: NoteType.ADDRESS,
        address: address1,
        showHashLink: true,
      },
      {
        type: NoteType.ADDRESS,
        address: address2,
        showHashLink: true,
      },
      {
        type: NoteType.ADDRESS,
        address: rawAddress3,
        showHashLink: true,
      },
    ];

    expect(formatted).toMatchObject(expected);
  });

  it('with Solana addresses', () => {
    const address1 = '7BgBvyjrZX1YKz4oh9mjb8ZScatkkwb8DzFx7LoiVkM3';
    const address2 = 'DYw8jCTfwHNRJhhmFcbXvVDTqWMEVFBX6ZKUmG5CNSKK';
    const notes = `Address ${address1},${address2}`;

    const formatted = get(formatNotes({ notes }));

    const expected: NoteFormat[] = [
      {
        type: NoteType.WORD,
        word: 'Address',
      },
      {
        type: NoteType.ADDRESS,
        address: address1,
        showHashLink: true,
      },
      {
        type: NoteType.ADDRESS,
        address: address2,
        showHashLink: true,
      },
    ];

    expect(formatted).toMatchObject(expected);
  });

  describe('with Tx Ref', () => {
    const txHash = '0xdb11f732bc83d29b52b20506cdd795196d3d0c5c42f9ad15b31bb4257c4990a5';
    const notes = `TxHash ${txHash}`;

    it('noTxRef = false', () => {
      const formatted = get(formatNotes({ notes }));

      const expected: NoteFormat[] = [
        {
          type: NoteType.WORD,
          word: 'TxHash',
        },
        {
          type: NoteType.TX,
          address: txHash,
          showHashLink: true,
        },
      ];

      expect(formatted).toMatchObject(expected);
    });

    it('multiple txHash', () => {
      const formatted = get(formatNotes({ notes: `TxHash ${txHash},${txHash}, ${txHash}` }));

      const expected: NoteFormat[] = [
        {
          type: NoteType.WORD,
          word: 'TxHash',
        },
        {
          type: NoteType.TX,
          address: txHash,
          showHashLink: true,
        },
        {
          type: NoteType.TX,
          address: txHash,
          showHashLink: true,
        },
        {
          type: NoteType.TX,
          address: txHash,
          showHashLink: true,
        },
      ];

      expect(formatted).toMatchObject(expected);
    });

    it('noTxRef = true', () => {
      const formatted = get(formatNotes({ notes, noTxRef: true }));

      const expected: NoteFormat[] = [
        {
          type: NoteType.WORD,
          word: `TxHash ${txHash}`,
        },
      ];

      expect(formatted).toMatchObject(expected);
    });
  });

  it('with Validator Index', () => {
    const validatorIndex = 201670;
    const notes = `Validator ${validatorIndex}`;

    const formatted = get(formatNotes({ notes, validatorIndex }));

    const expected: NoteFormat[] = [
      {
        type: NoteType.WORD,
        word: 'Validator',
      },
      {
        type: NoteType.ADDRESS,
        address: `${validatorIndex}`,
        chain: Blockchain.ETH2,
        showHashLink: true,
      },
    ];

    expect(formatted).toMatchObject(expected);
  });

  it('with Multiple Validator Indices', () => {
    const validatorIndex = 201670;
    const notes = `Validator ${validatorIndex},${validatorIndex}`;

    const formatted = get(formatNotes({ notes, validatorIndex }));

    const expected: NoteFormat[] = [
      {
        type: NoteType.WORD,
        word: 'Validator',
      },
      {
        type: NoteType.ADDRESS,
        address: `${validatorIndex}`,
        chain: Blockchain.ETH2,
        showHashLink: true,
      },
      {
        type: NoteType.ADDRESS,
        address: `${validatorIndex}`,
        chain: Blockchain.ETH2,
        showHashLink: true,
      },
    ];

    expect(formatted).toMatchObject(expected);
  });

  it('with Extra Data `sourceValidatorIndex` and `targetValidatorIndex`', () => {
    const sourceValidatorIndex = 812312;
    const targetValidatorIndex = 812311;
    const notes = `Consolidate ${sourceValidatorIndex} to ${targetValidatorIndex}`;

    const formatted = get(formatNotes({ notes, extraData: { sourceValidatorIndex, targetValidatorIndex } }));

    const expected: NoteFormat[] = [
      {
        type: NoteType.WORD,
        word: 'Consolidate',
      },
      {
        type: NoteType.ADDRESS,
        address: `${sourceValidatorIndex}`,
        chain: Blockchain.ETH2,
        showHashLink: true,
      },
      {
        type: NoteType.WORD,
        word: 'to',
      },
      {
        type: NoteType.ADDRESS,
        address: `${targetValidatorIndex}`,
        chain: Blockchain.ETH2,
        showHashLink: true,
      },
    ];

    expect(formatted).toMatchObject(expected);
  });

  it('with Block Number', () => {
    const blockNumber = 17173975;
    const notes = `BlockNo ${blockNumber}`;

    const formatted = get(formatNotes({ notes, blockNumber }));

    const expected: NoteFormat[] = [
      {
        type: NoteType.WORD,
        word: 'BlockNo',
      },
      {
        type: NoteType.BLOCK,
        address: `${blockNumber}`,
        showHashLink: true,
      },
    ];

    expect(formatted).toMatchObject(expected);
  });

  it('with Multiple Block Numbers', () => {
    const blockNumber = 17173975;
    const notes = `BlockNo ${blockNumber},${blockNumber}`;

    const formatted = get(formatNotes({ notes, blockNumber }));

    const expected: NoteFormat[] = [
      {
        type: NoteType.WORD,
        word: 'BlockNo',
      },
      {
        type: NoteType.BLOCK,
        address: `${blockNumber}`,
        showHashLink: true,
      },
      {
        type: NoteType.BLOCK,
        address: `${blockNumber}`,
        showHashLink: true,
      },
    ];

    expect(formatted).toMatchObject(expected);
  });

  it('with evm asset identifier', () => {
    const notes = 'Sell eip155:1/erc20:0x514910771AF9Ca656af840dff83E8264EcF986CA';

    const formatted = get(formatNotes({ notes }));

    const expected: NoteFormat[] = [
      {
        type: NoteType.WORD,
        word: 'Sell USDC',
      },
    ];

    expect(formatted).toMatchObject(expected);
  });

  it('scramble IBAN', async () => {
    await store.updateSetting({ scrambleData: false });
    const iban = 'DE88 5678 9012 1234 345 67';
    const notes = `Send 8,325.00 EURe via bank transfer to Rotki Solutions GmbH (${iban}) with memo "for salaries and insurance"`;

    const notesData = formatNotes({ notes, counterparty: 'monerium' });
    let formatted = get(notesData);
    let notesToString = formatted
      .filter(item => item.type === NoteType.WORD)
      .map(item => item.word)
      .join('');

    expect(notesToString).toContain(iban);

    await store.updateSetting({ scrambleData: true });
    formatted = get(notesData);
    notesToString = formatted
      .filter(item => item.type === NoteType.WORD)
      .map(item => item.word)
      .join('');

    expect(notesToString).not.toContain(iban);
  });

  it('works with punctuation', () => {
    const address = '0xCb2286d9471cc185281c4f763d34A962ED212962';
    const notes = `Address ${address}, ${address}. Some sentence.`;

    const formatted = get(formatNotes({ notes }));

    const expected: NoteFormat[] = [
      {
        type: NoteType.WORD,
        word: 'Address',
      },
      {
        type: NoteType.ADDRESS,
        address,
        showHashLink: true,
      },
      {
        type: NoteType.ADDRESS,
        address,
        showHashLink: true,
      },
      {
        type: NoteType.WORD,
        word: '. Some sentence.',
      },
    ];

    expect(formatted).toMatchObject(expected);
  });

  it('should properly handle an asset resolving to empty string', () => {
    const notes = 'Sell JUNO for USD. Amount out';
    const formatted = get(formatNotes({ notes, assetId: '0xdeadbeef' }));
    expect(formatted).toMatchObject([{ type: 'word', word: 'Sell JUNO for USD. Amount out' }]);
  });

  it('should handle amount for gnosis pay event notes properly', () => {
    const notes = 'Pay 1500 CHF (84.12 EUR) to merchant.';

    const formatted = get(formatNotes({ notes, counterparty: 'gnosis_pay' }));

    const expected: NoteFormat[] = [
      {
        type: NoteType.WORD,
        word: 'Pay',
      },
      {
        type: NoteType.AMOUNT,
        amount: bigNumberify(1500),
      },
      {
        type: NoteType.WORD,
        word: 'CHF (',
      },
      {
        type: NoteType.AMOUNT,
        amount: bigNumberify(84.12),
        asset: undefined,
      },
      {
        type: NoteType.WORD,
        word: 'EUR) to merchant.',
      },
    ];

    expect(formatted).toMatchObject(expected);
  });

  it('should handle country flag for gnosis pay event notes', () => {
    const notes = 'Pay 8.5 EUR to Lidl in Berlin :country:DE:';

    const formatted = get(formatNotes({ notes, counterparty: 'gnosis_pay' }));

    const expected: NoteFormat[] = [
      {
        type: NoteType.WORD,
        word: 'Pay',
      },
      {
        type: NoteType.AMOUNT,
        amount: bigNumberify(8.5),
      },
      {
        type: NoteType.WORD,
        word: 'EUR to Lidl in Berlin',
      },
      {
        type: NoteType.FLAG,
        countryCode: 'de',
      },
    ];

    expect(formatted).toMatchObject(expected);
  });

  it('should handle merchant code for gnosis pay event notes', () => {
    const notes = 'Pay 8.5 EUR to :merchant_code:5411: Lidl in Berlin :country:DE:';

    const formatted = get(formatNotes({ notes, counterparty: 'gnosis_pay' }));

    const expected: NoteFormat[] = [
      {
        type: NoteType.WORD,
        word: 'Pay',
      },
      {
        type: NoteType.AMOUNT,
        amount: bigNumberify(8.5),
      },
      {
        type: NoteType.WORD,
        word: 'EUR to',
      },
      {
        type: NoteType.MERCHANT_CODE,
        merchantCode: '5411',
      },
      {
        type: NoteType.WORD,
        word: 'Lidl in Berlin',
      },
      {
        type: NoteType.FLAG,
        countryCode: 'de',
      },
    ];

    expect(formatted).toMatchObject(expected);
  });

  it('should not handle country flag or merchant code for non-gnosis_pay counterparty', () => {
    const notes = 'Pay 8.5 EUR to :merchant_code:5411: Lidl in Berlin :country:DE:';

    const formatted = get(formatNotes({ notes, counterparty: 'other' }));

    const expected: NoteFormat[] = [
      {
        type: NoteType.WORD,
        word: 'Pay 8.5 EUR to :merchant_code:5411: Lidl in Berlin :country:DE:',
      },
    ];

    expect(formatted).toMatchObject(expected);
  });
});
