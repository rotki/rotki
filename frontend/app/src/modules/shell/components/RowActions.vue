<script setup lang="ts">
import ConfirmPopover from '@/modules/shell/components/ConfirmPopover.vue';

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
   * `confirmLabel` defaults to "Delete".
   */
  deleteConfirm?: { message: string; title?: string; confirmLabel?: string };
}>();

const emit = defineEmits<{
  'edit-click': [];
  'delete-click': [];
}>();

defineSlots<{
  default: () => any;
}>();

const { t } = useI18n({ useScope: 'global' });

const editClick = (): void => emit('edit-click');
const deleteClick = (): void => emit('delete-click');

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
    <template v-if="!noDelete">
      <ConfirmPopover
        v-if="deleteConfirm"
        :title="deleteConfirm.title"
        :message="deleteConfirm.message"
        :confirm-label="deleteConfirm.confirmLabel ?? t('common.actions.delete')"
        @confirm="deleteClick()"
      >
        <template #activator="{ attrs }">
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
        </template>
      </ConfirmPopover>
      <RuiButton
        v-else
        :disabled="disabled || deleteDisabled"
        :title="deleteTooltip || undefined"
        variant="text"
        data-testid="row-delete"
        icon
        @click="deleteClick()"
      >
        <RuiIcon
          size="16"
          name="lu-trash-2"
        />
      </RuiButton>
    </template>
    <slot />
  </div>
</template>
