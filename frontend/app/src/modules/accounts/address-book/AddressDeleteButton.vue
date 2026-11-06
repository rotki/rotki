<script setup lang="ts">
import type { AddressBookEntry, AddressBookLocation } from '@/modules/accounts/address-book/eth-names';
import { AddressNamePriority } from '@/modules/accounts/address-book/types/address-name-priorities';
import { useAddressBookDeletion } from '@/modules/accounts/address-book/use-address-book-deletion';
import InlineConfirm from '@/modules/shell/components/InlineConfirm.vue';

interface AddressDeleteButtonProps {
  text: string;
  source: string | null;
}

const { text, source } = defineProps<AddressDeleteButtonProps>();

const { t } = useI18n({ useScope: 'global' });

/**
 * Whether the button has given way to its question.
 *
 * @remarks
 * The question replaces the button inside the hovered tooltip that holds it, rather than opening a
 * popover of its own: a popover is teleported out of that tooltip, so moving the pointer onto it
 * would close the tooltip and take the popover down with it.
 */
const asking = ref<boolean>(false);

const canDelete = computed<boolean>(() =>
  source === AddressNamePriority.PRIVATE_ADDRESSBOOK || source === AddressNamePriority.GLOBAL_ADDRESSBOOK,
);

const location = computed<AddressBookLocation>(() =>
  source === AddressNamePriority.GLOBAL_ADDRESSBOOK ? 'global' : 'private',
);

const { deleteConfirm, deleteEntry } = useAddressBookDeletion(location);

const entry = computed<AddressBookEntry>(() => ({
  address: text,
  blockchain: null,
  name: '',
}));

const question = computed<{ title: string; message: string }>(() => deleteConfirm(get(entry)));

async function confirmDelete(): Promise<void> {
  set(asking, false);
  await deleteEntry(get(entry));
}
</script>

<template>
  <template v-if="canDelete">
    <div
      v-if="asking"
      class="rounded-sm bg-rui-surface ml-1"
    >
      <InlineConfirm
        :title="question.title"
        :message="question.message"
        :confirm-label="t('common.actions.delete')"
        tone="error"
        @cancel="asking = false"
        @confirm="confirmDelete()"
      />
    </div>
    <RuiTooltip
      v-else
      :options="{ placement: 'top' }"
      :open-delay="400"
    >
      <template #activator>
        <RuiButton
          size="sm"
          variant="text"
          class="-my-0.5"
          icon
          data-testid="address-delete"
          @click="asking = true"
        >
          <template #prepend>
            <RuiIcon
              name="lu-trash-2"
              size="16"
              class="text-rui-grey-400!"
            />
          </template>
        </RuiButton>
      </template>
      {{ t('address_book.actions.delete.tooltip') }}
    </RuiTooltip>
  </template>
</template>
