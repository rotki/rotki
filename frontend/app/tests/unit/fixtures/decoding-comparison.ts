import { TransactionDecodingComparison } from '@/modules/history/data-issues/schemas';

export function createDecodingComparison(): TransactionDecodingComparison {
  const event = {
    amount: '2',
    asset: 'ETH',
    balanceEffect: '-2',
    customized: true,
    eventSubtype: null,
    eventType: 'spend',
    location: 'ethereum',
    locationLabel: '0x0000000000000000000000000000000000000001',
    sequenceIndex: 1,
    timestamp: 1710000000000,
    userNotes: 'My edited spend',
  };
  return TransactionDecodingComparison.parse({
    decodedEvents: [{ ...event, amount: '1', balanceEffect: '-1', customized: false, userNotes: 'Decoded spend' }],
    groupIdentifier: 'different-transaction',
    savedEvents: [event],
    txHash: `0x${'ab'.repeat(32)}`,
  });
}
