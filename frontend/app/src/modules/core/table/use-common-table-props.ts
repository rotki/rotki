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
  const modelOpenDialog = shallowRef<boolean>(false);
  const modelEditableItem = ref<V>();
  const itemsToDelete = ref<V[]>([]) as Ref<V[]>;
  const modelConfirmationMessage = shallowRef<string>('');
  const expanded = ref<V[]>([]) as Ref<V[]>;

  return {
    confirmationMessage: modelConfirmationMessage,
    editableItem: modelEditableItem,
    expanded,
    itemsToDelete,
    openDialog: modelOpenDialog,
    selected,
  };
}
