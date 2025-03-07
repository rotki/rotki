<script setup lang="ts">
import AddressBookManagement from '@/components/address-book-manager/AddressBookManagement.vue';
import { NoteLocation } from '@/types/notes';

definePage({
  meta: {
    noteLocation: NoteLocation.ADDRESS_BOOK_MANAGER,
  },
});
</script>

<template>
  <AddressBookManagement />
</template>
