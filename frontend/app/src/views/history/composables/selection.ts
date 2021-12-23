import { computed, ref, Ref } from '@vue/composition-api';
import isEqual from 'lodash/isEqual';
import sortBy from 'lodash/sortBy';
import * as logger from 'loglevel';

type IdType = string | number;

type GetId<T> = (item: T) => string | undefined;
export const setupSelectionMode = function <T>(
  data: Ref<Array<T>>,
  getId: GetId<T>
) {
  const selected = ref<string[]>([]);

  const isSelected = (id: IdType) => {
    return selected.value.includes(id.toString());
  };

  const selectionChanged = (id: IdType, select: boolean) => {
    const idString = id.toString();
    const selection = [...selected.value];
    if (!select) {
      const index = selection.indexOf(idString);
      if (index >= 0) {
        selection.splice(index, 1);
      }
    } else if (idString && !selection.includes(idString)) {
      selection.push(idString);
    }
    selected.value = selection;
  };

  const setAllSelected = (selectAll: boolean) => {
    const selection: string[] = [];
    if (selectAll) {
      for (const item of data.value) {
        const id = getId(item);
        const idString = id?.toString() ?? '';
        if (!idString || selection.includes(idString)) {
          logger.warn(
            'A problematic item has been detected, possible duplicate id',
            item
          );
        } else {
          selection.push(idString);
        }
      }
    }
    selected.value = selection;
  };

  const isAllSelected = computed(() => {
    const strings = data.value.map(getId);
    return (
      strings.length > 0 && isEqual(sortBy(strings), sortBy(selected.value))
    );
  });

  return {
    selected,
    isSelected,
    selectionChanged,
    setAllSelected,
    isAllSelected
  };
};
