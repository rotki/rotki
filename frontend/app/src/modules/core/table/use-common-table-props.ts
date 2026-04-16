import type { Ref } from 'vue';

interface UseCommonTablePropsReturn<V extends NonNullable<unknown>> {
  selected: Ref<V[]>;
  openDialog: Ref<boolean>;
  editableItem: Ref<V | undefined>;
  itemsToDelete: Ref<V[]>;
  confirmationMessage: Ref<string>;
  expanded: Ref<V[]>;
}

export function useCommonTableProps<V extends NonNullable<unknown>>(): UseCommonTablePropsReturn<V> {
  const selected = ref<V[]>([]) as Ref<V[]>;
  const openDialog = ref<boolean>(false);
  const editableItem = ref<V>();
  const itemsToDelete = ref<V[]>([]) as Ref<V[]>;
  const confirmationMessage = ref<string>('');
  const expanded = ref<V[]>([]) as Ref<V[]>;

  return {
    confirmationMessage,
    editableItem,
    expanded,
    itemsToDelete,
    openDialog,
    selected,
  };
}
