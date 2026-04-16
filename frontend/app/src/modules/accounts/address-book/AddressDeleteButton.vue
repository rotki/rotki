<script setup lang="ts">
import type { AddressBookEntry, AddressBookLocation } from '@/modules/accounts/address-book/eth-names';
import { AddressNamePriority } from '@/modules/accounts/address-book/types/address-name-priorities';
import { useAddressBookDeletion } from '@/modules/accounts/address-book/use-address-book-deletion';

interface AddressDeleteButtonProps {
  text: string;
  source: string | null;
}

const { text, source } = defineProps<AddressDeleteButtonProps>();

const canDelete = computed<boolean>(() =>
  source === AddressNamePriority.PRIVATE_ADDRESSBOOK || source === AddressNamePriority.GLOBAL_ADDRESSBOOK,
);

const location = computed<AddressBookLocation>(() =>
  source === AddressNamePriority.GLOBAL_ADDRESSBOOK ? 'global' : 'private',
);

const { t } = useI18n({ useScope: 'global' });

const { showDeleteConfirmation } = useAddressBookDeletion(location);

const entry = computed<AddressBookEntry>(() => ({
  address: text,
  blockchain: null,
  name: '',
}));

function handleDelete(): void {
  showDeleteConfirmation(get(entry));
}
</script>

<template>
  <RuiTooltip
    v-if="canDelete"
    :popper="{ placement: 'top' }"
    :open-delay="400"
  >
    <template #activator>
      <RuiButton
        size="sm"
        variant="text"
        class="-my-0.5"
        icon
        @click="handleDelete()"
      >
        <template #prepend>
          <RuiIcon
            name="lu-trash-2"
            size="16"
            class="!text-rui-grey-400"
          />
        </template>
      </RuiButton>
    </template>
    {{ t('address_book.actions.delete.tooltip') }}
  </RuiTooltip>
</template>
