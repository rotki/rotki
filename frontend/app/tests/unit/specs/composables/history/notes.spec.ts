import { Blockchain } from '@rotki/common/lib/blockchain';
import { type NoteFormat, NoteType } from '@/composables/history/events/notes';

vi.mock('@/composables/assets/retrieval', () => ({
  useAssetInfoRetrieval: vi.fn().mockReturnValue({
    assetSymbol: vi.fn().mockImplementation(identifier => identifier)
  })
}));

describe('composables::history/notes', () => {
  const { formatNotes } = useHistoryEventNote();

  test('Normal text', () => {
    const notes = 'Normal text';

    const formatted = get(formatNotes({ notes }));

    const expected: NoteFormat[] = [
      {
        type: NoteType.WORD,
        word: 'Normal'
      },
      {
        type: NoteType.WORD,
        word: 'text'
      }
    ];

    expect(formatted).toMatchObject(expected);
  });

  test('With amount and asset', () => {
    const notes = 'Receive 100 ETH';

    const formatted = get(
      formatNotes({ notes, amount: bigNumberify(100), assetId: 'ETH' })
    );

    const expected: NoteFormat[] = [
      {
        type: NoteType.WORD,
        word: 'Receive'
      },
      {
        type: NoteType.AMOUNT,
        amount: bigNumberify(100),
        asset: 'ETH'
      }
    ];

    expect(formatted).toMatchObject(expected);
  });

  test('With ETH address', () => {
    const address = '0xCb2286d9471cc185281c4f763d34A962ED212962';
    const notes = `Address ${address}`;

    const formatted = get(formatNotes({ notes }));

    const expected: NoteFormat[] = [
      {
        type: NoteType.WORD,
        word: 'Address'
      },
      {
        type: NoteType.ADDRESS,
        address,
        showIcon: true,
        showHashLink: true
      }
    ];

    expect(formatted).toMatchObject(expected);
  });

  describe('With TX Hash', () => {
    const txHash =
      '0xdb11f732bc83d29b52b20506cdd795196d3d0c5c42f9ad15b31bb4257c4990a5';
    const notes = `TxHash ${txHash}`;

    it('noTxHash = false', () => {
      const formatted = get(formatNotes({ notes }));

      const expected: NoteFormat[] = [
        {
          type: NoteType.WORD,
          word: 'TxHash'
        },
        {
          type: NoteType.TX,
          address: txHash,
          showHashLink: true
        }
      ];

      expect(formatted).toMatchObject(expected);
    });

    it('noTxHash = true', () => {
      const formatted = get(formatNotes({ notes, noTxHash: true }));

      const expected: NoteFormat[] = [
        {
          type: NoteType.WORD,
          word: 'TxHash'
        },
        {
          type: NoteType.WORD,
          word: txHash
        }
      ];

      expect(formatted).toMatchObject(expected);
    });
  });

  test('With Validator Index', () => {
    const validatorIndex = 201670;
    const notes = `Validator ${validatorIndex}`;

    const formatted = get(formatNotes({ notes, validatorIndex }));

    const expected: NoteFormat[] = [
      {
        type: NoteType.WORD,
        word: 'Validator'
      },
      {
        type: NoteType.ADDRESS,
        address: `${validatorIndex}`,
        chain: Blockchain.ETH2,
        showHashLink: true
      }
    ];

    expect(formatted).toMatchObject(expected);
  });

  test('With Block Number', () => {
    const blockNumber = 17173975;
    const notes = `BlockNo ${blockNumber}`;

    const formatted = get(formatNotes({ notes, blockNumber }));

    const expected: NoteFormat[] = [
      {
        type: NoteType.WORD,
        word: 'BlockNo'
      },
      {
        type: NoteType.BLOCK,
        address: `${blockNumber}`,
        showHashLink: true
      }
    ];

    expect(formatted).toMatchObject(expected);
  });
});
