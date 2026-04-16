import type { Collection } from '@/modules/common/collection';
import type {
  ProfitLossEvent,
  ReportActionableItem,
  ReportError,
  Reports,
} from '@/modules/reports/report-types';

function emptyError(): ReportError {
  return {
    error: '',
    message: '',
  };
}

function defaultReports(): Reports {
  return {
    entries: [],
    entriesFound: 0,
    entriesLimit: 0,
  };
}

export function defaultReportEvents(): Collection<ProfitLossEvent> {
  return {
    data: [],
    found: 0,
    limit: 0,
    total: 0,
  };
}

interface Progress {
  processingState: string;
  totalProgress: string;
}

function defaultProgress(): Progress {
  return {
    processingState: '',
    totalProgress: '',
  };
}

export const useReportsStore = defineStore('reports', () => {
  const reports = ref<Reports>(defaultReports());
  const reportProgress = ref<Progress>(defaultProgress());
  const reportError = ref(emptyError());
  const lastGeneratedReport = ref<number | null>(null);
  const actionableItems = ref<ReportActionableItem>({
    missingAcquisitions: [],
    missingPrices: [],
  });

  const isLatestReport = (reportId: number): ComputedRef<boolean> => computed<boolean>(() => get(lastGeneratedReport) === reportId);

  const progress = computed<string>(() => get(reportProgress).totalProgress);
  const processingState = computed<string>(() => get(reportProgress).processingState);

  const clearError = (): void => {
    set(reportError, emptyError());
  };

  const reset = (): void => {
    set(reports, defaultReports());
    clearError();
  };

  return {
    actionableItems,
    clearError,
    isLatestReport,
    lastGeneratedReport,
    processingState,
    progress,
    reportError,
    reportProgress,
    reports,
    reset,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useReportsStore, import.meta.hot));
