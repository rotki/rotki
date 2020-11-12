<template>
  <uniswap />
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import Uniswap from '@/components/defi/uniswap/Uniswap.vue';

@Component({
  components: { Uniswap }
})
export default class Liquidity extends Vue {}
</script>
