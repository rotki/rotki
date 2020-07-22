'use strict';
// Picked from https://github.com/negibouze/customize-no-unused-components-rule
// ------------------------------------------------------------------------------
// Requirements
// ------------------------------------------------------------------------------

const utils = require('eslint-plugin-vue/lib/utils');
const casing = require('eslint-plugin-vue/lib/utils/casing');
const cloneDeep = require('lodash/cloneDeep');

const myUtils = cloneDeep(utils);
const originalIsVueComponentFile = myUtils.isVueComponentFile;
myUtils.isVueComponentFile = (node, path) => {
  return (
    originalIsVueComponentFile.call(myUtils, node, path) ||
    node.declaration.type === 'ClassDeclaration'
  );
};

// ------------------------------------------------------------------------------
// Rule Definition
// ------------------------------------------------------------------------------

module.exports = {
  meta: {
    type: 'suggestion',
    docs: {
      description:
        'disallow registering components that are not used inside templates',
      category: 'essential'
    },
    fixable: null,
    schema: [
      {
        type: 'object',
        properties: {
          ignoreWhenBindingPresent: {
            type: 'boolean'
          }
        },
        additionalProperties: false
      }
    ]
  },

  create(context) {
    const options = context.options[0] || {};
    const ignoreWhenBindingPresent =
      options.ignoreWhenBindingPresent !== undefined
        ? options.ignoreWhenBindingPresent
        : true;
    const usedComponents = new Set();
    let registeredComponents = [];
    let ignoreReporting = false;
    let templateLocation;

    return myUtils.defineTemplateBodyVisitor(
      context,
      {
        VElement(node) {
          if (
            (!myUtils.isHtmlElementNode(node) &&
              !myUtils.isSvgElementNode(node)) ||
            myUtils.isHtmlWellKnownElementName(node.rawName) ||
            myUtils.isSvgWellKnownElementName(node.rawName)
          ) {
            return;
          }

          usedComponents.add(node.rawName);
        },
        "VAttribute[directive=true][key.name='bind'][key.argument='is']"(node) {
          if (
            !node.value || // `<component :is>`
            node.value.type !== 'VExpressionContainer' ||
            !node.value.expression // `<component :is="">`
          )
            return;

          if (node.value.expression.type === 'Literal') {
            usedComponents.add(node.value.expression.value);
          } else if (ignoreWhenBindingPresent) {
            ignoreReporting = true;
          }
        },
        "VAttribute[directive=false][key.name='is']"(node) {
          usedComponents.add(node.value.value);
        },
        "VElement[name='template']"(rootNode) {
          templateLocation = templateLocation || rootNode.loc.start;
        },
        "VElement[name='template']:exit"(rootNode) {
          if (
            rootNode.loc.start !== templateLocation ||
            ignoreReporting ||
            myUtils.hasAttribute(rootNode, 'src')
          )
            return;

          registeredComponents
            .filter(({ name }) => {
              // If the component name is PascalCase or camelCase
              // it can be used in various of ways inside template,
              // like "theComponent", "The-component" etc.
              // but except snake_case
              if (
                casing.pascalCase(name) === name ||
                casing.camelCase(name) === name
              ) {
                return ![...usedComponents].some(n => {
                  return (
                    n.indexOf('_') === -1 &&
                    (name === casing.pascalCase(n) ||
                      casing.camelCase(n) === name)
                  );
                });
              }
              // In any other case the used component name must exactly match
              // the registered name
              return !usedComponents.has(name);
            })
            .forEach(({ node, name }) =>
              context.report({
                node,
                message:
                  'The "{{name}}" component has been registered but not used.',
                data: {
                  name
                }
              })
            );
        }
      },
      myUtils.executeOnVue(context, obj => {
        if (obj.type === 'ClassDeclaration') {
          registeredComponents = getRegisteredComponentsFromClassDeclaration(
            obj
          );
        } else {
          registeredComponents = myUtils.getRegisteredComponents(obj);
        }
      })
    );
  }
};

const getRegisteredComponentsFromClassDeclaration = obj => {
  const decorators = obj.decorators;
  if (!decorators) return [];
  const expression = decorators[0].expression;
  const hasArguments =
    expression && expression.arguments && expression.arguments.length >= 1;
  return hasArguments
    ? myUtils.getRegisteredComponents(expression.arguments[0])
    : [];
};
