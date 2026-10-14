<script setup lang="ts">
import type { AddressBookLocation } from '@/modules/accounts/address-book/eth-names';
import { msg } from '@/message-key';
import AddressBookManagement from '@/modules/accounts/address-book/AddressBookManagement.vue';
import { NoteLocation } from '@/modules/core/common/notes';

definePage({
  meta: {
    nav: {
      labelKey: msg.$t('navigation_menu.manage_address_book'),
      icon: 'lu-book-text',
      section: 2,
      order: 40,
      drawer: 'address-book-manager',
    },
    noteLocation: NoteLocation.ADDRESS_BOOK_MANAGER,
  },
  // the router only matches the two books; without one, the page shows the global book
  path: '/address-book-manager/:tab(global|private)?',
  props: true,
});

const { tab } = defineProps<{
  tab?: string;
}>();

const router = useRouter();

/** The book in view lives in the route, so a reload or a shared link opens the same one. */
const location = computed<AddressBookLocation>({
  get: () => (tab === 'private' ? 'private' : 'global'),
  set: (value) => {
    if (value !== get(location))
      router.push(`/address-book-manager/${value}`);
  },
});
</script>

<template>
  <AddressBookManagement v-model:location="location" />
</template>
