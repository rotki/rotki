import { describe, expect, it } from 'vitest';
import { assetUpdateActivity } from '@/modules/assets/assets.activity';
import { activityLabel, activityLabelOf } from '@/modules/task-center/activity-labels';
import { ActivityKind, ActivityPart } from '@/modules/task-center/core/types';

describe('activityLabelOf', () => {
  it('should resolve the label of the kind and part the descriptor submits under', () => {
    expect(activityLabelOf(assetUpdateActivity, { version: 3 }))
      .toStrictEqual(activityLabel(ActivityKind.ASSETS, ActivityPart.UPDATE, { version: 3 }));
  });

  it('should pass the plural choice through', () => {
    expect(activityLabelOf(assetUpdateActivity, { version: 3 }, 2)?.plural).toBe(2);
  });

  it('should give no label to a descriptor without a fixed part', () => {
    expect(activityLabelOf({ kind: ActivityKind.ASSETS })).toBeUndefined();
  });

  it('should give no label to a pair with no entry', () => {
    expect(activityLabelOf({ kind: ActivityKind.PRICES, part: ActivityPart.LATEST })).toBeUndefined();
  });
});
