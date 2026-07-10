import type { CsvImportResult } from '../types/status-types';
import { NotificationCategory, Priority, Severity } from '@rotki/common';
import { mockT } from '@test/i18n';
import { describe, expect, it } from 'vitest';
import { createCsvImportResultHandler } from '@/modules/core/messaging/handlers/csv-import-result';

function result(overrides: Partial<CsvImportResult> = {}): CsvImportResult {
  return {
    messages: [],
    processed: 10,
    sourceName: 'binance',
    total: 10,
    ...overrides,
  };
}

describe('createCsvImportResultHandler', () => {
  it('should produce an info notification for a fully processed import', async () => {
    const handler = createCsvImportResultHandler(mockT);
    const notification = await handler.handle(result({ processed: 10, total: 10 }));

    expect(notification.severity).toBe(Severity.INFO);
    expect(notification.category).toBe(NotificationCategory.DEFAULT);
    expect(notification.priority).toBe(Priority.HIGH);
    expect(notification.display).toBe(true);
  });

  it('should warn when only part of the rows were processed', async () => {
    const handler = createCsvImportResultHandler(mockT);
    const notification = await handler.handle(result({ processed: 4, total: 10 }));

    expect(notification.severity).toBe(Severity.WARNING);
  });

  it('should error when nothing was processed', async () => {
    const handler = createCsvImportResultHandler(mockT);
    const notification = await handler.handle(result({ processed: 0, total: 10 }));

    expect(notification.severity).toBe(Severity.ERROR);
  });

  it('should append error messages to the body', async () => {
    const handler = createCsvImportResultHandler(mockT);
    const notification = await handler.handle(result({
      messages: [{ isError: true, msg: 'bad row' }],
      processed: 9,
      total: 10,
    }));

    expect(notification.message).toContain('1. bad row');
  });

  it('should render the affected rows when present', async () => {
    const handler = createCsvImportResultHandler(mockT);
    const notification = await handler.handle(result({
      messages: [{ isError: true, msg: 'bad row', rows: [1, 2, 3] }],
      processed: 9,
      total: 10,
    }));

    expect(notification.message).toContain('1-3');
  });

  it('should ignore negative row indices', async () => {
    const handler = createCsvImportResultHandler(mockT);
    const notification = await handler.handle(result({
      messages: [{ isError: true, msg: 'bad row', rows: [-1] }],
      processed: 9,
      total: 10,
    }));

    // Only the "rows:" line is skipped; the message line itself is kept.
    expect(notification.message).not.toContain('csv_import_result.rows');
    expect(notification.message).toContain('1. bad row');
  });
});
