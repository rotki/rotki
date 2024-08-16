import { Blockchain } from '@rotki/common';
import { describe, expect, it, vi } from 'vitest';
import { type NoteFormat, NoteType } from '@/composables/history/events/notes';

vi.mock('@/composables/assets/retrieval', () => ({
  useAssetInfoRetrieval: vi.fn().mockReturnValue({
    assetSymbol: vi.fn().mockImplementation((identifier) => {
      if (isEvmIdentifier(identifier))
        return 'USDC';

      return identifier;
    }),
  }),
}));

describe('composables::history/notes', () => {
  setActivePinia(createPinia());
  const { formatNotes } = useHistoryEventNote();
  const store = useSessionSettingsStore();

  it('normal text', () => {
    const notes = 'Normal text';

    const formatted = get(formatNotes({ notes }));

    const expected: NoteFormat[] = [
      {
        type: NoteType.WORD,
        word: 'Normal',
      },
      {
        type: NoteType.WORD,
        word: 'text',
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
        showIcon: true,
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
        showIcon: true,
        showHashLink: true,
      },
      {
        type: NoteType.ADDRESS,
        address,
        showIcon: true,
        showHashLink: true,
      },
    ];

    expect(formatted).toMatchObject(expected);
  });

  describe('with TX Hash', () => {
    const txHash = '0xdb11f732bc83d29b52b20506cdd795196d3d0c5c42f9ad15b31bb4257c4990a5';
    const notes = `TxHash ${txHash}`;

    it('noTxHash = false', () => {
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

    it('noTxHash = true', () => {
      const formatted = get(formatNotes({ notes, noTxHash: true }));

      const expected: NoteFormat[] = [
        {
          type: NoteType.WORD,
          word: 'TxHash',
        },
        {
          type: NoteType.WORD,
          word: txHash,
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
        word: 'Sell',
      },
      {
        type: NoteType.WORD,
        word: 'USDC',
      },
    ];

    expect(formatted).toMatchObject(expected);
  });

  it('scramble IBAN', () => {
    store.update({ scrambleData: false });
    const iban = 'DE88 5678 9012 1234 345 67';
    const notes = `Send 8,325.00 EURe via bank transfer to Rotki Solutions GmbH (${iban}) with memo "for salaries and insurance`;

    const notesData = formatNotes({ notes, counterparty: 'monerium' });
    let formatted = get(notesData);
    let notesToString = formatted
      .filter(item => item.type === NoteType.WORD)
      .map(item => item.word)
      .join('');
    let included = notesToString.includes(iban.split(' ').join(''));

    expect(included).toBeTruthy();

    store.update({ scrambleData: true });
    formatted = get(notesData);
    notesToString = formatted
      .filter(item => item.type === NoteType.WORD)
      .map(item => item.word)
      .join('');
    included = notesToString.includes(iban.split(' ').join(''));

    expect(included).toBeFalsy();
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
        showIcon: true,
        showHashLink: true,
      },
      {
        type: NoteType.ADDRESS,
        address,
        showIcon: true,
        showHashLink: true,
      },
      {
        type: NoteType.WORD,
        word: '.',
      },
      {
        type: NoteType.WORD,
        word: 'Some',
      },
      {
        type: NoteType.WORD,
        word: 'sentence.',
      },
    ];

    expect(formatted).toMatchObject(expected);
  });
});
