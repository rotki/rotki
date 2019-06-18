<template>
  <div :id="name + '_badge'" class="exchange-badge">
    <img
      :title="name"
      class="exchange-icon"
      :src="require(`../assets/images/${name}.png`)"
      alt="Exchange icon"
    />
    <div class="badge-name">{{ name }}</div>
  </div>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';

@Component({})
export default class ExchangeBadge extends Vue {
  @Prop({ required: true })
  name!: string;
}
</script>

<style scoped lang="scss">
.exchange-badge {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  max-width: 95px;
  padding: 8px;
}
.badge-name {
  font-size: 28px;
}
</style>
