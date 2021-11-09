<template>
  <v-card>
    <v-card-title>
      {{ title }}
      <v-spacer />
      <premium-lock />
    </v-card-title>
  </v-card>
</template>

<script lang="ts">
import { defineComponent } from '@vue/composition-api';
import PremiumLock from '../premium/PremiumLock.vue';

export default defineComponent({
  name: 'PremiumCard',
  components: { PremiumLock },
  props: {
    title: {
      required: true,
      type: String
    }
  }
});
</script>
