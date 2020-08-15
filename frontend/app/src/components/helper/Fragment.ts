/**
 * A workaround component to handle multiple root in a vue template
 * To be replaced by Fragment component when implemented by Vue itself
 */
const Fragment = {
  functional: true,
  render: (h: any, ctx: any) => ctx.children
};

export default Fragment;
