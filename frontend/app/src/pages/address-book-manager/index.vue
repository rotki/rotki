<script setup lang="ts">
import { NoteLocation } from '@/types/notes';
import AddressBookManagement from '@/components/address-book-manager/AddressBookManagement.vue';

definePage({
  meta: {
    noteLocation: NoteLocation.ADDRESS_BOOK_MANAGER,
  },
});
</script>

<template>
  <AddressBookManagement />
</template>
