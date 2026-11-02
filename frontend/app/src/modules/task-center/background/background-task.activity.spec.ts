import type { BackgroundTask } from './background-task-types';
import { describe, expect, it } from 'vitest';
import { activitySubject } from '@/modules/task-center/activity-subject';
import { type Activity, ActivityKind, ActivitySourceType, ActivityStatus } from '@/modules/task-center/core/types';
import { backgroundTaskActivity, backgroundTaskLabel } from './background-task.activity';

const address = '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c';

function task(kind: string, subject: BackgroundTask['subject']): BackgroundTask {
  return { id: 5, kind, name: `backend name of ${kind}`, startedAt: 1, subject };
}

function asActivity(background: BackgroundTask): Activity {
  return {
    cancellable: false,
    id: backgroundTaskActivity.id(background),
    kind: ActivityKind.BACKGROUND_TASK,
    percentage: -1,
    rerunnable: false,
    source: { type: ActivitySourceType.NATIVE },
    status: ActivityStatus.RUNNING,
    title: 'Background tasks',
  };
}

const chainName = (chain: string): string => `chain ${chain}`;

describe('background task activity', () => {
  it.each([
    ['evm_transactions', { address, chain: 'eth' }, { address, chain: 'eth' }],
    ['evm_receipts', { chain: 'optimism', count: 3 }, { chain: 'optimism' }],
    ['transaction_decoding', { chain: 'base', count: 10 }, { chain: 'base' }],
    ['xpub_derivation', { chain: 'btc' }, { chain: 'btc' }],
    ['exchange_history', { location: 'kraken', name: 'my kraken' }, { location: 'kraken' }],
  ] as const)('should give a %s row its icon and link from the id', (kind, subject, expected) => {
    expect(activitySubject(asActivity(task(kind, subject)))).toStrictEqual(expected);
  });

  it('should give a task without a subject no icon', () => {
    expect(activitySubject(asActivity(task('db_upload', {})))).toBeUndefined();
  });

  it('should put only the address in a transaction query\'s subtitle, so the row can link it', () => {
    expect(backgroundTaskLabel(task('evm_transactions', { address, chain: 'eth' }), chainName)).toStrictEqual({
      key: 'task_center.activity.background_task.evm_transactions',
      params: { address },
      plural: undefined,
    });
  });

  it('should count the transactions a decode covers', () => {
    expect(backgroundTaskLabel(task('transaction_decoding', { chain: 'base', count: 10 }), chainName)).toStrictEqual({
      key: 'task_center.activity.background_task.transaction_decoding',
      params: { chain: 'chain base', count: 10 },
      plural: 10,
    });
  });

  it('should fall back to the backend\'s own name for a kind this build does not know', () => {
    expect(backgroundTaskLabel(task('something_new', {}), chainName)).toBe('backend name of something_new');
  });
});
