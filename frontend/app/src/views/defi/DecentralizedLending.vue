<template>
  <lending></lending>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import Lending from '@/components/defi/Lending.vue';

@Component({
  components: { Lending }
})
export default class DecentralizedLoans extends Vue {}
</script>

<style scoped></style>
