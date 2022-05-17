<template>
  <v-tooltip bottom>
    <template #activator="{ on }">
      <v-badge color="transparent" offset-y="20" offset-x="20">
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
          <v-icon color="primary" small>mdi-lock</v-icon>
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
