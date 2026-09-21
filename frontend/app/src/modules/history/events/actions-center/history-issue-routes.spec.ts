import type { ActionTarget } from '@/modules/core/action-center/types';
import { describe, expect, it } from 'vitest';
import { DuplicateHandlingStatus } from '@/modules/history/events/action-types';
import { duplicatesRoute, toGlobalTarget } from '@/modules/history/events/actions-center/history-issue-routes';
import { DIALOG_TYPES } from '@/modules/history/events/dialog-types';
import { PinnedNames, toPinned } from '@/modules/session/types';

describe('modules/history/events/actions-center/history-issue-routes', () => {
  it('should route a dialog to the history page with the query that opens it', () => {
    expect(toGlobalTarget({ kind: 'dialog', options: { type: DIALOG_TYPES.MATCH_ASSET_MOVEMENTS } })).toEqual({
      kind: 'route',
      to: { name: '/history/events/', query: { openMatchAssetMovementsDialog: 'true' } },
    });
  });

  it('should land on the history page for a dialog no query can open', () => {
    expect(toGlobalTarget({ kind: 'dialog', options: { type: DIALOG_TYPES.ADD_TRANSACTION } })).toEqual({
      kind: 'route',
      to: { name: '/history/events/' },
    });
  });

  it('should open a dialog over the history page the user is on, keeping its filters and replacing the entry', () => {
    const pageQuery = { limit: '25', location: 'kraken', page: '3' };

    expect(toGlobalTarget({ kind: 'dialog', options: { type: DIALOG_TYPES.MATCH_ASSET_MOVEMENTS } }, pageQuery)).toEqual({
      kind: 'route',
      to: {
        name: '/history/events/',
        query: { ...pageQuery, openMatchAssetMovementsDialog: 'true' },
        replace: true,
      },
    });
  });

  it('should leave the history page as it is for a dialog no query can open', () => {
    const pageQuery = { location: 'kraken' };

    expect(toGlobalTarget({ kind: 'dialog', options: { type: DIALOG_TYPES.ADD_TRANSACTION } }, pageQuery)).toEqual({
      kind: 'route',
      to: { name: '/history/events/', query: pageQuery, replace: true },
    });
  });

  it('should route duplicates to the events list filtered to their groups', () => {
    expect(toGlobalTarget({ groupIds: ['a', 'b'], kind: 'duplicates', status: DuplicateHandlingStatus.AUTO_FIX })).toEqual({
      kind: 'route',
      to: duplicatesRoute(['a', 'b'], DuplicateHandlingStatus.AUTO_FIX),
    });
    expect(duplicatesRoute(['a', 'b'], DuplicateHandlingStatus.AUTO_FIX)).toEqual({
      name: '/history/events/',
      query: { duplicateHandlingStatus: DuplicateHandlingStatus.AUTO_FIX, groupIdentifiers: 'a,b' },
    });
  });

  it.each<ActionTarget>([
    { kind: 'pin', panel: toPinned(PinnedNames.DATA_ISSUES, {}) },
    { kind: 'external', url: 'https://docs.rotki.com' },
    { kind: 'route', to: { name: '/history/events/' } },
  ])('should pass a $kind target, which already works from anywhere, through unchanged', (target) => {
    expect(toGlobalTarget(target)).toBe(target);
  });
});
