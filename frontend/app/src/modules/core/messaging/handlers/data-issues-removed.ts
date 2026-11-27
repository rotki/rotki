import type { StateHandler } from '../interfaces';
import { startPromise } from '@shared/utils';
import { createStateHandler } from '@/modules/core/messaging/utils';
import { useDataIssuesInboxStore } from '@/modules/history/data-issues/use-data-issues-inbox-store';
import { useDataIssuesSummary } from '@/modules/history/data-issues/use-data-issues-summary';

interface DataIssuesRemovedData {
  assets: string[];
}

export function createDataIssuesRemovedHandler(): StateHandler<DataIssuesRemovedData> {
  const dataIssuesInboxStore = useDataIssuesInboxStore();
  const { refreshSummary: refreshDataIssuesSummary } = useDataIssuesSummary();

  return createStateHandler<DataIssuesRemovedData>((data) => {
    dataIssuesInboxStore.notifyIssuesChanged(data.assets);
    if (!dataIssuesInboxStore.hasActiveReloadListeners)
      startPromise(refreshDataIssuesSummary());
  });
}
