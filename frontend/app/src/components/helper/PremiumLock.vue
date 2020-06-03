<template>
  <v-tooltip top>
    <template #activator="{ on }">
      <v-btn
        text
        icon
        v-bind="lockSize"
        :href="$interop.isPackaged ? undefined : $interop.premiumURL"
        v-on="on"
        @click="$interop.isPackaged ? $interop.navigateToPremium() : undefined"
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
import { Vue, Component, Prop } from 'vue-property-decorator';

@Component({})
export default class PremiumLock extends Vue {
  @Prop({ type: String, required: false, default: '' })
  size!: string;

  get lockSize() {
    if (this.size !== '') return { [this.size]: true };
    return null;
  }
}
</script>
