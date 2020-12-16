<template>
  <v-container>
    <!-- insert components to be tested here -->
    <linear-progress />
    <circlular-progress />
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import CirclularProgress from '@/components/helper/CirclularProgress.vue';
import LinearProgress from '@/components/helper/LinearProgress.vue';

@Component({
  components: { CirclularProgress, LinearProgress }
})
export default class Playground extends Vue {}
</script>
