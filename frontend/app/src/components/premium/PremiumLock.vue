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
        <v-icon>mdi-lock</v-icon>
      </v-btn>
    </template>
    <span v-text="$t('premium_lock.tooltip')" />
  </v-tooltip>
</template>
<script lang="ts">
import { Vue, Component, Prop } from 'vue-property-decorator';

@Component({})
export default class PremiumLock extends Vue {
  // Supply a `size` (x-small, small, large, x-large)
  @Prop({ type: String, required: false, default: '' })
  size!: string;

  // Changes the size of the button based on the `size` prop
  get lockSize() {
    if (this.size !== '') return { [this.size]: true };
    return null;
  }
}
</script>
