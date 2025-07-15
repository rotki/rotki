import type { CommonMessageHandler, CsvImportResult } from '@/types/websocket-messages';
import { type Notification, Priority, Severity } from '@rotki/common';
import { groupConsecutiveNumbers } from '@/utils/text';

export function useCsvImportResultHandler(t: ReturnType<typeof useI18n>['t']): CommonMessageHandler<CsvImportResult> {
  const handle = (data: CsvImportResult): Notification => {
    const { messages, processed, sourceName, total } = data;
    const title = t('notification_messages.csv_import_result.title', { sourceName });
    let messageBody = t('notification_messages.csv_import_result.summary', {
      imported: processed,
      total,
    });
    if (messages.length > 0) {
      messageBody = `${messageBody}\n\n${t('notification_messages.csv_import_result.errors')}`;
      messages.forEach((error, index) => {
        messageBody = `${messageBody}\n${index + 1}. ${error.msg}`;
        if (error.rows)
          messageBody = `${messageBody}\n${t('notification_messages.csv_import_result.rows', { rows: groupConsecutiveNumbers(error.rows) }, error.rows.length)}`;
      });
    }
    let severity: Severity;
    if (processed === 0)
      severity = Severity.ERROR;
    else if (processed < total)
      severity = Severity.WARNING;
    else
      severity = Severity.INFO;
    return {
      display: true,
      message: messageBody,
      priority: Priority.HIGH,
      severity,
      title,
    };
  };

  return { handle };
};
