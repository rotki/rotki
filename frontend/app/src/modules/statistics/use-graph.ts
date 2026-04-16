import type { GradientArea, NewGraphApi } from '@rotki/common';
import { useDarkMode } from '@/modules/shell/theme/use-dark-mode';

// vue-echarts THEME_KEY constant - defined inline to avoid pulling in echarts to main bundle
const THEME_KEY = 'ecTheme';

export function useGraph(): NewGraphApi {
  const { isDark } = useRotkiTheme();
  const { store } = useRotkiTheme();
  const { usedTheme } = useDarkMode();

  provide(THEME_KEY, store);

  const white = '#ffffff';
  const secondaryBlack = '#3f1300';

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

  const secondaryColor = computed<string>(() => (get(isDark) ? white : secondaryBlack));

  return {
    baseColor,
    gradient,
    secondaryColor,
  };
}
