<template>
  <div :id="`${name}_badge`" class="exchange-badge">
    <v-img
      :title="name"
      contain
      class="exchange-badge__icon"
      :src="require(`../assets/images/${name}.png`)"
      alt="Exchange icon"
    />
    <div class="exchange-badge__name">{{ name }}</div>
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
  flex-direction: row;
  align-items: center;
  width: 350px;
  padding: 8px;
}

.exchange-badge__icon {
  height: 50px;
  max-width: 50px;
  filter: grayscale(100%);
}

.exchange-badge__name {
  margin-left: 16px;
  padding: 8px;
  font-size: 30px;
}
</style>
