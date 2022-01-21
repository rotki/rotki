<template>
  <tr>
    <td
      :colspan="$vuetify.breakpoint.xsOnly ? 2 : colspan"
      class="upgrade-row font-weight-medium"
    >
      <i18n
        v-if="events"
        tag="span"
        path="upgrade_row.events"
        class="d-flex flex-row justify-center align-end"
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
        <template #from>
          <date-display class="mx-1" :timestamp="timeStart" />
        </template>
        <template #to>
          <date-display class="ms-1" :timestamp="timeEnd" />
        </template>
      </i18n>
      <i18n
        v-else
        tag="span"
        path="upgrade_row.upgrade"
        class="d-flex flex-row justify-center align-end"
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
  </tr>
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
  @Prop({ required: false, type: Boolean, default: false })
  events!: boolean;
  @Prop({ required: false, type: Number, default: 0 })
  timeStart!: number;
  @Prop({ required: false, type: Number, default: 0 })
  timeEnd!: number;
}
</script>

<style>
.upgrade-row {
  height: 60px;
}
</style>
