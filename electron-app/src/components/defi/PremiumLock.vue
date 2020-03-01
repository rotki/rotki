<template>
  <v-tooltip top>
    <template #activator="{ on }">
      <v-btn
        text
        icon
        :href="$interop.isPackaged ? undefined : $interop.premiumURL"
        v-on="on"
        @click="$interop.isPackaged ? $interop.upgradePremium() : undefined"
      >
        <v-icon>fa-lock</v-icon>
      </v-btn>
    </template>
    <span>
      Feature is only supported with a premium subscription
    </span>
  </v-tooltip>
</template>
<script lang="ts">
import { Vue, Component } from 'vue-property-decorator';

@Component({})
export default class PremiumLock extends Vue {}
</script>
