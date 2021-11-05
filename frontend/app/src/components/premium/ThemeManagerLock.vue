<template>
  <div class="theme-manager">
    <div class="text-h6 mt-4">{{ $t('theme_manager_lock.title') }}</div>
    <div class="text-subtitle-1">{{ $t('theme_manager_lock.subtitle') }}</div>
    <v-sheet outlined rounded>
      <v-row align="center" class="py-3 px-2">
        <v-col cols="auto">
          <premium-lock />
        </v-col>
        <v-col>{{ $t('theme_manager_lock.description') }}</v-col>
      </v-row>
    </v-sheet>
  </div>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import PremiumLock from '@/components/premium/PremiumLock.vue';

@Component({
  name: 'ThemeManagerLock',
  components: { PremiumLock }
})
export default class ThemeManagerLock extends Vue {}
</script>
