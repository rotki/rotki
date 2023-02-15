/* eslint-disable unicorn/prefer-modern-dom-apis */
import Vue from 'vue';
import { assert } from '@/utils/assertions';

const freeze = (object: any, property: any, value: any) => {
  Object.defineProperty(object, property, {
    configurable: true,
    get() {
      return value;
    },
    set(v) {
      // eslint-disable-next-line no-console
      console.warn(`tried to set frozen property ${property} with ${v}`);
    }
  });
};

const unfreeze = (object: any, property: any, value = null) => {
  Object.defineProperty(object, property, {
    configurable: true,
    writable: true,
    value
  });
};

//TODO: remove after upgrading to Vue 3.x
export default Vue.extend({
  // @ts-ignore
  abstract: true,
  name: 'Fragment',

  props: {
    name: {
      type: String,
      default: () => Math.floor(Date.now() * Math.random()).toString(16)
    }
  },

  mounted() {
    const container = this.$el;
    const parent = container.parentNode;

    assert(container);
    assert(parent);

    const name1 = this.$props.name;
    const head = document.createComment(`fragment#${name1}#head`);
    const tail = document.createComment(`fragment#${name1}#tail`);

    parent.insertBefore(head, container);
    parent.insertBefore(tail, container);

    container.appendChild = node => {
      parent.insertBefore(node, tail);
      freeze(node, 'parentNode', container);
      return node;
    };

    container.insertBefore = (node, ref) => {
      parent.insertBefore(node, ref);
      freeze(node, 'parentNode', container);
      return node;
    };

    container.removeChild = node => {
      parent.removeChild(node);
      unfreeze(node, 'parentNode');
      return node;
    };

    Array.from(container.childNodes).forEach(node =>
      container.appendChild(node)
    );

    parent.removeChild(container);

    freeze(container, 'parentNode', parent);
    freeze(container, 'nextSibling', tail.nextSibling);

    const insertBefore = parent.insertBefore;
    parent.insertBefore = (node, ref) => {
      insertBefore.call(parent, node, ref !== container ? ref : head);
      return node;
    };

    const removeChild = parent.removeChild;
    parent.removeChild = node => {
      if ((node as Node) === container) {
        while (head.nextSibling !== tail) {
          if (!head.nextSibling) {
            continue;
          }
          container.removeChild(head.nextSibling);
        }

        parent.removeChild(head);
        parent.removeChild(tail);
        unfreeze(container, 'parentNode');

        parent.insertBefore = insertBefore;
        parent.removeChild = removeChild;
      } else {
        removeChild.call(parent, node);
      }
      return node;
    };
  },

  render(h) {
    const children = this.$slots.default;

    // add fragment attribute on the children
    const fragment = this.$props.name;
    if (children && children.length > 0) {
      children.forEach(
        child =>
          (child.data = {
            ...child.data,
            attrs: { fragment, ...(child.data || {}).attrs }
          })
      );
    }

    return h('div', { attrs: { fragment } }, children);
  }
});
