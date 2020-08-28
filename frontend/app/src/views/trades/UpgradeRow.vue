<template>
  <td :colspan="colspan" class="upgrade-row font-weight-medium">
    <i18n
      tag="span"
      path="upgrade_row.upgrade"
      class="d-flex flex-row justify-center"
    >
      <template #total>
        {{ total }}
      </template>
      <template #limit>
        {{ limit }}
      </template>
      <template #label>
        {{ label }}
      </template>
      <template #link>
        <base-external-link
          class="ml-1"
          :text="$t('upgrade_row.rotki_premium')"
          :href="$interop.premiumURL"
        />
      </template>
    </i18n>
  </td>
</template>
<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import BaseExternalLink from '@/components/base/BaseExternalLink.vue';

@Component({
  components: {
    BaseExternalLink
  }
})
export default class UpgradeRow extends Vue {
  @Prop({ required: true, type: Number })
  colspan!: number;
  @Prop({ required: true, type: String })
  label!: string;
  @Prop({ required: true, type: Number })
  total!: number;
  @Prop({ required: true, type: Number })
  limit!: number;
}
</script>

<style>
.upgrade-row {
  height: 60px;
}
</style>
