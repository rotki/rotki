<script lang="ts" setup>
import { useAddressBookForm } from '@/composables/address-book/form';

const props = defineProps<{
  text: string;
  blockchain: string;
  name?: string;
}>();

const emit = defineEmits<{
  open: [];
}>();

const { t } = useI18n({ useScope: 'global' });
const { showGlobalDialog } = useAddressBookForm();

function openAddressBookForm() {
  emit('open');
  showGlobalDialog({
    address: props.text,
    blockchain: props.blockchain,
    name: props.name || '',
  });
}
</script>

<template>
  <RuiTooltip
    :popper="{ placement: 'top' }"
    :open-delay="400"
  >
    <template #activator>
      <RuiButton
        size="sm"
        variant="text"
        class="-my-0.5"
        icon
        @click="openAddressBookForm()"
      >
        <template #prepend>
          <RuiIcon
            name="lu-pencil"
            size="16"
            class="!text-rui-grey-400"
          />
        </template>
      </RuiButton>
    </template>
    {{ t('address_book.actions.edit.tooltip') }}
  </RuiTooltip>
</template>
