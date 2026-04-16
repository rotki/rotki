<script setup lang="ts">
import AddressBookManagement from '@/modules/accounts/address-book/AddressBookManagement.vue';
import { NoteLocation } from '@/modules/core/common/notes';

definePage({
  meta: {
    noteLocation: NoteLocation.ADDRESS_BOOK_MANAGER,
  },
});
</script>

<template>
  <AddressBookManagement />
</template>
