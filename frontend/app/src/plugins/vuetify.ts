/* istanbul ignore file */

import '@mdi/font/css/materialdesignicons.css';
import Vue from 'vue';
import Vuetify from 'vuetify';
import { VDialog, VNavigationDrawer } from 'vuetify/lib/components';
import DiscordIcon from '@/components/svgs/DiscordIcon.vue';
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

// Fix scroll error issue on VOverlay
const newShouldScroll = (el: Element, e: WheelEvent): boolean => {
  if (el.tagName === 'BODY' || el.tagName === 'HTML') {
    return false;
  }
  if (el.hasAttribute('data-app')) {
    return false;
  }

  const dir = e.shiftKey || e.deltaX ? 'x' : 'y';
  const delta = dir === 'y' ? e.deltaY : e.deltaX || e.deltaY;

  let alreadyAtStart: boolean;
  let alreadyAtEnd: boolean;
  if (dir === 'y') {
    alreadyAtStart = el.scrollTop === 0;
    alreadyAtEnd = el.scrollTop + el.clientHeight === el.scrollHeight;
  } else {
    alreadyAtStart = el.scrollLeft === 0;
    alreadyAtEnd = el.scrollLeft + el.clientWidth === el.scrollWidth;
  }

  const scrollingUp = delta < 0;
  const scrollingDown = delta > 0;

  if (!alreadyAtStart && scrollingUp) {
    return true;
  }
  if (!alreadyAtEnd && scrollingDown) {
    return true;
  }
  if (alreadyAtStart || alreadyAtEnd) {
    return newShouldScroll(el.parentNode as Element, e);
  }

  return false;
};

// @ts-ignore
VDialog.options.mixins[2].options.methods.shouldScroll = newShouldScroll;

// @ts-ignore
VNavigationDrawer.options.mixins[2].options.methods.shouldScroll =
  newShouldScroll;

const DARK_GREY = '#1e1e1e';

const vuetify = new Vuetify({
  icons: {
    iconfont: 'mdi',
    values: {
      discord: {
        component: DiscordIcon
      }
    }
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
