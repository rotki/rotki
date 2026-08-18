import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { createMock } from '@test/utils/create-mock';
import { describe, expect, it } from 'vitest';
import { IssueKind, IssueState, NON_TERMINAL_STATES } from '@/modules/history/data-issues/constants';
import {
  asMulti,
  asSingle,
  buildPanelPayload,
  PANEL_PAGE_SIZE,
  panelFilterFields,
} from '@/modules/history/data-issues/data-issues-panel-utils';
import { DataIssuesFilterKeys } from '@/modules/history/data-issues/use-data-issues-filter';

function field(key: string): FieldDef {
  return createMock<FieldDef>({ key });
}

describe('panelFilterFields', () => {
  it('should keep only the four fields that fit the preview', () => {
    const fields = [
      field(DataIssuesFilterKeys.STATE),
      field(DataIssuesFilterKeys.KIND),
      field(DataIssuesFilterKeys.ASSET),
      field(DataIssuesFilterKeys.ACCOUNT),
      field(DataIssuesFilterKeys.START),
      field(DataIssuesFilterKeys.END),
    ];

    expect(panelFilterFields(fields).map(f => f.key)).toStrictEqual([
      DataIssuesFilterKeys.STATE,
      DataIssuesFilterKeys.KIND,
      DataIssuesFilterKeys.ASSET,
      DataIssuesFilterKeys.ACCOUNT,
    ]);
  });

  it('should drop the period pills, which the preview does not offer', () => {
    const keys = panelFilterFields([field(DataIssuesFilterKeys.START), field(DataIssuesFilterKeys.END)]);

    expect(keys).toStrictEqual([]);
  });

  it('should preserve the order the caller supplied', () => {
    const fields = [field(DataIssuesFilterKeys.ACCOUNT), field(DataIssuesFilterKeys.STATE)];

    expect(panelFilterFields(fields).map(f => f.key)).toStrictEqual([
      DataIssuesFilterKeys.ACCOUNT,
      DataIssuesFilterKeys.STATE,
    ]);
  });
});

describe('asMulti', () => {
  it('should pass a string through', () => {
    expect(asMulti('ETH')).toBe('ETH');
  });

  it('should pass an array through', () => {
    expect(asMulti(['a', 'b'])).toStrictEqual(['a', 'b']);
  });

  it('should drop a boolean, which the payload cannot carry', () => {
    expect(asMulti(true)).toBeUndefined();
    expect(asMulti(false)).toBeUndefined();
  });

  it('should drop undefined', () => {
    expect(asMulti(undefined)).toBeUndefined();
  });
});

describe('asSingle', () => {
  it('should pass a string through', () => {
    expect(asSingle('ETH')).toBe('ETH');
  });

  it('should drop an array, since the field takes one value', () => {
    expect(asSingle(['a', 'b'])).toBeUndefined();
  });

  it('should drop a boolean and undefined', () => {
    expect(asSingle(true)).toBeUndefined();
    expect(asSingle(undefined)).toBeUndefined();
  });
});

describe('buildPanelPayload', () => {
  it('should default to the non-terminal states when no state filter is engaged', () => {
    const payload = buildPanelPayload({}, 0);

    expect(payload.state).toStrictEqual([...NON_TERMINAL_STATES]);
  });

  it('should not fall back once the user picks a state', () => {
    const payload = buildPanelPayload({ state: [IssueState.RESOLVED] }, 0);

    expect(payload.state).toStrictEqual([IssueState.RESOLVED]);
  });

  it('should carry the offset and a fixed page size', () => {
    const payload = buildPanelPayload({}, 50);

    expect(payload.offset).toBe(50);
    expect(payload.limit).toBe(PANEL_PAGE_SIZE);
  });

  it('should map asset and account to single values and kind to a multi value', () => {
    const payload = buildPanelPayload({
      asset: 'ETH',
      kind: [IssueKind.NEGATIVE_BALANCE, IssueKind.UNMATCHED_BRIDGE],
      locationLabel: '0x01',
    }, 0);

    expect(payload.asset).toBe('ETH');
    expect(payload.locationLabel).toBe('0x01');
    expect(payload.kind).toStrictEqual([IssueKind.NEGATIVE_BALANCE, IssueKind.UNMATCHED_BRIDGE]);
  });

  it('should leave an unset filter off the payload rather than sending an empty value', () => {
    const payload = buildPanelPayload({}, 0);

    expect(payload.asset).toBeUndefined();
    expect(payload.kind).toBeUndefined();
    expect(payload.locationLabel).toBeUndefined();
  });
});
