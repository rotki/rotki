import type { GradientArea, NewGraphApi } from '@rotki/common';
import { useDarkMode } from '@/modules/shell/theme/use-dark-mode';

// vue-echarts THEME_KEY constant - defined inline to avoid pulling in echarts to main bundle
const THEME_KEY = 'ecTheme';

export function useGraph(): NewGraphApi {
  const { isDark } = useRotkiTheme();
  const { store } = useRotkiTheme();
  const { usedTheme } = useDarkMode();

  provide(THEME_KEY, store);

  // neutral greys, so only the theme's graph color carries hue
  const secondaryLight = '#3f3f46';
  const secondaryDark = '#d4d4d8';

  const baseColor = computed<string>(() => get(usedTheme).graph);

  const gradient = computed<GradientArea>(() => {
    const color = get(baseColor);
    const colorStops = [
      { color: `${color}80`, offset: 0 },
      { color: `${color}00`, offset: 1 },
    ];
    return {
      color: {
        colorStops,
        type: 'linear',
        x: 0,
        x2: 0,
        y: 0,
        y2: 1,
      },
    };
  });

  const secondaryColor = computed<string>(() => (get(isDark) ? secondaryDark : secondaryLight));

  return {
    baseColor,
    gradient,
    secondaryColor,
  };
}
