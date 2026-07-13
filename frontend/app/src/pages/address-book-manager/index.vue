<script setup lang="ts">
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
});
</script>

<template>
  <AddressBookManagement />
</template>
