/* istanbul ignore file */

import '@mdi/font/css/materialdesignicons.css';
import Vue from 'vue';
import Vuetify from 'vuetify';
import {
  DARK_ACCENT,
  DARK_ERROR,
  DARK_GRAPH,
  DARK_INFO,
  DARK_PRIMARY,
  DARK_SUCCESS,
  DARK_WARNING,
  LIGHT_ACCENT,
  LIGHT_ERROR,
  LIGHT_GRAPH,
  LIGHT_INFO,
  LIGHT_PRIMARY,
  LIGHT_SUCCESS,
  LIGHT_WARNING
} from '@/plugins/theme';

Vue.use(Vuetify);

const DARK_GREY = '#1e1e1e';

const vuetify = new Vuetify({
  icons: {
    iconfont: 'mdi'
  },
  theme: {
    options: {
      customProperties: true
    },
    themes: {
      light: {
        primary: LIGHT_PRIMARY,
        secondary: '#0a0908',
        accent: LIGHT_ACCENT,
        graph: LIGHT_GRAPH,
        graphFade: '#ffffff',
        error: LIGHT_ERROR,
        success: LIGHT_SUCCESS,
        info: LIGHT_INFO,
        warning: LIGHT_WARNING,
        'rotki-light-grey': '#f9fafb',
        'rotki-grey': '#9fa6b2',
        'rotki-scrollbar': '#eeeeee'
      },
      dark: {
        primary: DARK_PRIMARY,
        accent: DARK_ACCENT,
        graph: DARK_GRAPH,
        graphFade: DARK_GREY,
        dark: DARK_GREY,
        error: DARK_ERROR,
        success: DARK_SUCCESS,
        info: DARK_INFO,
        warning: DARK_WARNING,
        'rotki-light-grey': '#121212',
        'rotki-scrollbar': '#999999'
      }
    }
  }
});

export { vuetify };
