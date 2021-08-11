import { computed, ref, Ref } from '@vue/composition-api';
import isEqual from 'lodash/isEqual';
import sortBy from 'lodash/sortBy';
import * as logger from 'loglevel';

type GetId<T> = (item: T) => string | undefined;
export const setupSelectionMode = function <T>(
  data: Ref<Array<T>>,
  getId: GetId<T>
) {
  const selected = ref<string[]>([]);
  const setSelected = (selectAll: boolean) => {
    const selection: string[] = [];
    if (selectAll) {
      for (const item of data.value) {
        const id = getId(item);
        if (!id || selection.includes(id)) {
          logger.warn(
            'A problematic item has been detected, possible duplicate id',
            item
          );
        } else {
          selection.push(id);
        }
      }
    }
    selected.value = selection;
  };

  const selectionChanged = (id: string, select: boolean) => {
    const selection = [...selected.value];
    if (!select) {
      const index = selection.indexOf(id);
      if (index >= 0) {
        selection.splice(index, 1);
      }
    } else if (id && !selection.includes(id)) {
      selection.push(id);
    }
    selected.value = selection;
  };

  const allSelected = computed(() => {
    const strings = data.value.map(getId);
    return (
      strings.length > 0 && isEqual(sortBy(strings), sortBy(selected.value))
    );
  });

  return {
    selected,
    setSelected,
    selectionChanged,
    allSelected
  };
};
