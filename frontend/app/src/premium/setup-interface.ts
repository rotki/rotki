import Chart from 'chart.js';
import moment from 'moment';
import Vue from 'vue';
import Vuex from 'vuex';
import { TIME_UNIT_DAY } from '@/components/dashboard/const';
import { TimeUnit } from '@/components/dashboard/types';
import { displayDateFormatter } from '@/data/date_formatter';
import { registerComponents } from '@/premium/register-components';
import { DataUtilities, DateUtilities } from '@/premium/types';
import store from '@/store/store';

const date: DateUtilities = {
  epoch(): number {
    return moment().unix();
  },
  format(date: string, oldFormat: string, newFormat: string): string {
    return moment(date, oldFormat).format(newFormat);
  },
  now(format: string): string {
    return moment().format(format);
  },
  epochToFormat(epoch: number, format: string): string {
    return moment(epoch * 1000).format(format);
  },
  dateToEpoch(date: string, format: string): number {
    return moment(date, format).unix();
  },
  epochStartSubtract(amount: number, unit: TimeUnit): number {
    return moment().subtract(amount, unit).startOf(TIME_UNIT_DAY).unix();
  },
  toUserSelectedFormat(timestamp: number): string {
    return displayDateFormatter.format(
      new Date(timestamp * 1000),
      store.getters['session/dateDisplayFormat']
    );
  }
};

const data: DataUtilities = {
  assetInfo: (identifier: string) => {
    return store.getters['balances/assetInfo'](identifier);
  },
  getIdentifierForSymbol: (symbol: string) => {
    return store.getters['balances/getIdentifierForSymbol'](symbol);
  }
};

export const setupPremium = () => {
  window.Vue = Vue;
  window.Chart = Chart;
  window.Vue.use(Vuex);
  window.moment = moment;
  window.rotki = {
    useHostComponents: true,
    version: 11,
    utils: {
      date,
      data
    }
  };
  registerComponents();
};
