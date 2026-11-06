<script setup lang="ts">
import type { AddressBookEntry, AddressBookLocation } from '@/modules/accounts/address-book/eth-names';
import type { ConfirmQuestion } from '@/modules/shell/components/confirm-question';
import { AddressNamePriority } from '@/modules/accounts/address-book/types/address-name-priorities';
import { useAddressBookDeletion } from '@/modules/accounts/address-book/use-address-book-deletion';
import ConfirmInPlace from '@/modules/shell/components/ConfirmInPlace.vue';
import { useDeleteQuestion } from '@/modules/shell/components/row-delete-question';

/**
 * Deletes an address book name from the tooltip of the address it labels.
 *
 * @remarks
 * The question replaces the button inside the hovered tooltip that holds it, rather than opening a
 * popover of its own: a popover is teleported out of that tooltip, so moving the pointer onto it
 * would close the tooltip and take the popover down with it. The question sits on the surface
 * colour, since its tint alone would let the tooltip show through.
 */
const { text, source } = defineProps<{
  text: string;
  source: string | null;
}>();

const { t } = useI18n({ useScope: 'global' });
const toDeleteQuestion = useDeleteQuestion();

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

const question = computed<ConfirmQuestion>(() => toDeleteQuestion(deleteConfirm(get(entry))));

async function confirmDelete(): Promise<void> {
  await deleteEntry(get(entry));
}
</script>

<template>
  <ConfirmInPlace
    v-if="canDelete"
    class="rounded-sm bg-rui-surface ml-1"
    :question="question"
    @confirm="confirmDelete()"
  >
    <template #activator="{ ask }">
      <RuiTooltip
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
            @click="ask()"
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
  </ConfirmInPlace>
</template>
