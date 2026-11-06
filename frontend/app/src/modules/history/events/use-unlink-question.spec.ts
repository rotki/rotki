import { describe, expect, it } from 'vitest';
import { useUnlinkQuestion } from '@/modules/history/events/use-unlink-question';

describe('use-unlink-question', () => {
  const { unlinkQuestion } = useUnlinkQuestion();

  it('should ask about a matched asset movement with the movement wording', () => {
    expect(unlinkQuestion({ type: 'asset-movement' })).toEqual({
      confirmLabel: 'transactions.events.actions.unlink',
      message: 'transactions.events.confirmation.unlink.message',
      title: 'transactions.events.confirmation.unlink.title',
    });
  });

  it('should ask about a bridge transfer with the bridge wording', () => {
    expect(unlinkQuestion({ hasSynthetic: false, type: 'bridge' }).message).toBe(
      'transactions.events.confirmation.unlink.bridge_message',
    );
  });

  it('should warn that unlinking deletes a counterpart rotki created', () => {
    expect(unlinkQuestion({ hasSynthetic: true, type: 'bridge' }).message).toBe(
      'transactions.events.confirmation.unlink.bridge_synthetic_message',
    );
  });
});
