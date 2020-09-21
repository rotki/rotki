<template>
  <borrowing />
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import Borrowing from '@/components/defi/Borrowing.vue';

@Component({
  components: { Borrowing }
})
export default class DecentralizedBorrowing extends Vue {}
</script>
