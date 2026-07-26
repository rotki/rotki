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
  const modelSelected = shallowRef<V[]>([]);
  const modelOpenDialog = shallowRef<boolean>(false);
  const modelEditableItem = ref<V>();
  const modelItemsToDelete = shallowRef<V[]>([]);
  const modelConfirmationMessage = shallowRef<string>('');
  const modelExpanded = shallowRef<V[]>([]);

  return {
    confirmationMessage: modelConfirmationMessage,
    editableItem: modelEditableItem,
    expanded: modelExpanded,
    itemsToDelete: modelItemsToDelete,
    openDialog: modelOpenDialog,
    selected: modelSelected,
  };
}
