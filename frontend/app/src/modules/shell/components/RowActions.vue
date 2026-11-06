<script setup lang="ts">
import type { ConfirmQuestion } from '@/modules/shell/components/confirm-question';
import ConfirmPopover from '@/modules/shell/components/ConfirmPopover.vue';
import { type RowDeleteQuestion, useDeleteQuestion } from '@/modules/shell/components/row-delete-question';

const { disabled = false, editDisabled = false, editTooltip = '', noEdit = false, deleteDisabled = false, deleteTooltip = '', noDelete = false, align = 'start', deleteConfirm } = defineProps<{
  disabled?: boolean;
  editDisabled?: boolean;
  editTooltip?: string;
  noEdit?: boolean;
  deleteDisabled?: boolean;
  deleteTooltip?: string;
  noDelete?: boolean;
  align?: 'start' | 'center' | 'end';
  /**
   * When set, the delete button asks in a popover beside it, and `delete-click` means confirmed.
   * `confirmLabel` defaults to "Delete" and `tone` to `error`.
   */
  deleteConfirm?: RowDeleteQuestion;
}>();

const emit = defineEmits<{
  'edit-click': [];
  'delete-click': [];
}>();

defineSlots<{
  default: () => any;
}>();

/** The delete button, bound to the popover's activator `attrs` or, without a question, to a plain click. */
const [DefineDeleteButton, ReuseDeleteButton] = createReusableTemplate<{ attrs: Record<string, unknown> }>();

const editClick = (): void => emit('edit-click');
const deleteClick = (): void => emit('delete-click');

const toDeleteQuestion = useDeleteQuestion();
const deleteQuestion = computed<ConfirmQuestion | undefined>(() => deleteConfirm && toDeleteQuestion(deleteConfirm));

const justify = computed<string>(() => {
  const justify = {
    center: 'justify-center',
    end: 'justify-end',
    start: 'justify-start',
  } as const;
  return justify[align];
});
</script>

<template>
  <div
    class="flex flex-nowrap items-center gap-1"
    :class="justify"
  >
    <RuiButton
      v-if="!noEdit"
      :disabled="disabled || editDisabled"
      :title="editTooltip || undefined"
      variant="text"
      data-testid="row-edit"
      icon
      @click="editClick()"
    >
      <RuiIcon
        size="16"
        name="lu-pencil"
      />
    </RuiButton>
    <DefineDeleteButton #default="{ attrs }">
      <RuiButton
        :disabled="disabled || deleteDisabled"
        :title="deleteTooltip || undefined"
        variant="text"
        data-testid="row-delete"
        icon
        v-bind="attrs"
      >
        <RuiIcon
          size="16"
          name="lu-trash-2"
        />
      </RuiButton>
    </DefineDeleteButton>
    <template v-if="!noDelete">
      <ConfirmPopover
        v-if="deleteQuestion"
        :question="deleteQuestion"
        @confirm="deleteClick()"
      >
        <template #activator="{ attrs }">
          <ReuseDeleteButton :attrs="attrs" />
        </template>
      </ConfirmPopover>
      <ReuseDeleteButton
        v-else
        :attrs="{ onClick: deleteClick }"
      />
    </template>
    <slot />
  </div>
</template>
