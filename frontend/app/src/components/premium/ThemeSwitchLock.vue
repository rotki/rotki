<template>
  <v-tooltip top>
    <template #activator="{ on }">
      <v-badge color="transparent" offset-y="40" offset-x="35">
        <v-btn
          text
          icon
          target="_blank"
          class="secondary--text text--lighten-4"
          :href="$interop.isPackaged ? undefined : $interop.premiumURL"
          v-on="on"
          @click="
            $interop.isPackaged ? $interop.navigateToPremium() : undefined
          "
        >
          <v-icon>mdi-white-balance-sunny</v-icon>
        </v-btn>
        <template #badge>
          <v-icon color="primary">mdi-lock</v-icon>
        </template>
      </v-badge>
    </template>
    <span>
      {{ $t('theme_switch_lock.tooltip') }}
    </span>
  </v-tooltip>
</template>
<script lang="ts">
import { defineComponent } from '@vue/composition-api';

export default defineComponent({
  name: 'ThemeSwitchLock'
});
</script>
