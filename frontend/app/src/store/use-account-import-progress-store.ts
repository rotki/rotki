import type { ComputedRef, Ref } from 'vue';
import { assert } from '@rotki/common';

export class TotalNotInitializedError extends Error {
  constructor() {
    super();
    this.name = 'TotalNotInitializedError';
  }
}

export class TotalCannotBeNegativeError extends Error {
  constructor() {
    super();
    this.name = 'TotalCannotBeNegativeError';
  }
}

interface AccountImportProgress {
  readonly total: number;
  readonly current: number;
  readonly skipped: number;
}

interface UseAccountImportProgressStoreReturn {
  increment: () => void;
  importingAccounts: ComputedRef<boolean>;
  progress: Readonly<Ref<AccountImportProgress>>;
  progressPercentage: ComputedRef<number>;
  setTotal: (total?: number) => void;
  skip: () => void;
}

export const useAccountImportProgressStore = defineStore('import-progress', (): UseAccountImportProgressStoreReturn => {
  const progress = ref<AccountImportProgress>({
    current: 0,
    skipped: 0,
    total: 0,
  });

  const importingAccounts = computed<boolean>(() => get(progress).total > 0);
  const progressPercentage = computed<number>(() => Math.round((get(progress).current / get(progress).total) * 100));

  function skip(): void {
    const currentProgress = get(progress);
    if (currentProgress.total === 0) {
      throw new TotalNotInitializedError();
    }
    assert(currentProgress.total > 0, 'setTotal should be called first');
    set(progress, {
      ...currentProgress,
      current: currentProgress.current + 1,
      skipped: currentProgress.skipped + 1,
    });
  }

  function increment(): void {
    const currentProgress = get(progress);
    if (currentProgress.total === 0) {
      throw new TotalNotInitializedError();
    }
    set(progress, {
      ...currentProgress,
      current: currentProgress.current + 1,
    });
  }

  function setTotal(total: number = 0): void {
    if (total < 0) {
      throw new TotalCannotBeNegativeError();
    }
    const currentProgress = get(progress);
    set(progress, {
      ...(total === 0 ? { current: 0, skipped: 0 } : currentProgress),
      total,
    });
  }

  return {
    importingAccounts,
    increment,
    progress,
    progressPercentage,
    setTotal,
    skip,
  };
});
