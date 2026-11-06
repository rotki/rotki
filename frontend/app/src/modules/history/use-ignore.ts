import type { Ref } from 'vue';
import type {
  IgnorePayload,
} from '@/modules/history/ignored';
import type { EntryMeta } from '@/modules/history/meta';
import { err, type Result } from 'plainfp/result';
import { fromPromise, map } from 'plainfp/result-async';
import { uniqueStrings } from '@/modules/core/common/data/data';
import { useHistoryIgnoringApi } from '@/modules/history/api/use-history-ignoring-api';

interface CommonIgnoreAction<T extends EntryMeta> {
  toData: (t: T) => string;
}

interface UseIgnoreReturn<T extends EntryMeta> {
  ignore: (ignored: boolean) => Promise<Result<void, unknown>>;
  ignoreSingle: (item: T, ignored: boolean) => Promise<Result<void, unknown>>;
  toggle: (item: T) => Promise<Result<void, unknown>>;
}

/**
 * Excludes the selected entries from accounting, or includes them again.
 *
 * @remarks
 * Reports nothing itself: every action returns an `Err` for the surface that started it to name,
 * holding the request's own error, or the reason nothing was sent when no entry needed the change.
 */
export function useIgnore<T extends EntryMeta>(
  { toData }: CommonIgnoreAction<T>,
  selected: Ref<T[]>,
  refresh: () => any,
): UseIgnoreReturn<T> {
  const { t } = useI18n({ useScope: 'global' });
  const api = useHistoryIgnoringApi();

  async function ignoreInAccounting(payload: IgnorePayload, ignore: boolean): Promise<Result<void, unknown>> {
    const request = ignore ? api.ignoreActions(payload) : api.unignoreActions(payload);
    return map(fromPromise(request, (error: unknown) => error), () => undefined);
  }

  const ignore = async (ignored: boolean): Promise<Result<void, unknown>> => {
    const data = get(selected).filter((item) => {
      const { ignoredInAccounting } = item;
      return ignored ? !ignoredInAccounting : ignoredInAccounting;
    });

    if (data.length === 0)
      return err(t('ignore.no_items.description', ignored ? 1 : 2));

    const outcome = await ignoreInAccounting({ data: data.map(toData).filter(uniqueStrings) }, ignored);

    if (outcome.ok) {
      refresh();
      set(selected, []);
    }
    return outcome;
  };

  async function toggle(item: T): Promise<Result<void, unknown>> {
    set(selected, [item]);
    return ignore(!item.ignoredInAccounting);
  }

  async function ignoreSingle(item: T, ignored: boolean): Promise<Result<void, unknown>> {
    set(selected, [item]);
    return ignore(ignored);
  }

  return {
    ignore,
    ignoreSingle,
    toggle,
  };
}
