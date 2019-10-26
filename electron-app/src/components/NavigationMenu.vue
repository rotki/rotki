<template>
  <div class="sidebar-nav navbar-collapse">
    <ul id="side-menu" class="nav">
      <li>
        <router-link to="/">
          <i class="fa fa-dashboard fa-fw"></i>Dashboard
        </router-link>
      </li>
      <li>
        <a>
          <i class="fa fa-exchange fa-fw"></i>Trade
          <span class="fa arrow"></span>
        </a>
        <ul class="nav nav-second-level">
          <li>
            <router-link to="/otc-trades">OTC Trades</router-link>
          </li>
          <li>
            <a href="#">Exchange Trades</a>
          </li>
        </ul>
      </li>
      <li>
        <router-link to="/statistics">
          <i class="fa fa-bar-chart fa-fw"></i>Statistics
        </router-link>
      </li>
      <li>
        <router-link to="/tax-report">
          <i class="fa fa-calculator fa-fw"></i>Tax Report
        </router-link>
      </li>
    </ul>
  </div>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';

@Component({})
export default class NavigationMenu extends Vue {}
</script>

<style scoped></style>
