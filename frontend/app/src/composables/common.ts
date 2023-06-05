export const useProxy = () => {
  const currentInstance = getCurrentInstance();
  assert(currentInstance?.proxy);
  return currentInstance.proxy;
};

export const useTheme = () => {
  const { $vuetify } = useProxy();
  const theme = computed(() => $vuetify.theme);
  const dark = computed(() => $vuetify.theme.dark);

  const fontStyle = computed(() => ({
    color: get(dark) ? 'rgba(255,255,255,0.87)' : 'rgba(0,0,0,0.87)'
  }));

  const appBarColor = computed(() => {
    if (!get(dark)) {
      return 'white';
    }
    return null;
  });

  return {
    $vuetify,
    theme,
    dark,
    fontStyle,
    appBarColor
  };
};

export const useDisplay = () => {
  const { $vuetify } = useProxy();
  const mobile = computed(() => $vuetify.breakpoint.mobile);
  const name = computed(() => $vuetify.breakpoint.name);
  const width = computed(() => $vuetify.breakpoint.width);

  const xs = computed(() => $vuetify.breakpoint.xs);
  const sm = computed(() => $vuetify.breakpoint.sm);
  const md = computed(() => $vuetify.breakpoint.md);
  const lg = computed(() => $vuetify.breakpoint.lg);
  const xl = computed(() => $vuetify.breakpoint.xl);
  const smAndDown = computed(() => $vuetify.breakpoint.smAndDown);
  const smAndUp = computed(() => $vuetify.breakpoint.smAndUp);
  const mdAndDown = computed(() => $vuetify.breakpoint.mdAndDown);
  const mdAndUp = computed(() => $vuetify.breakpoint.mdAndUp);
  const lgAndDown = computed(() => $vuetify.breakpoint.lgAndDown);
  const lgAndUp = computed(() => $vuetify.breakpoint.lgAndUp);

  return {
    xs,
    sm,
    md,
    lg,
    xl,
    smAndDown,
    smAndUp,
    mdAndDown,
    mdAndUp,
    lgAndDown,
    lgAndUp,
    mobile,
    name,
    width
  };
};
