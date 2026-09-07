/**
 * Local ESLint rules for this workspace, registered under the `local/` plugin namespace in
 * `eslint.config.js`.
 *
 * @remarks
 * The comment rules that used to live here, `no-comment-run` and `tsdoc-on-declaration`, now ship
 * in `@rotki/eslint-plugin`. What remains is domain-specific and has no home outside this repo.
 *
 * @packageDocumentation
 */

/** The submission helpers whose `run` body is skipped entirely for a deduped caller. */
const ACTIVITY_SUBMITTERS = new Set(['submitTask', 'submitExclusiveTask']);

/**
 * Reports a `run` body that returns its result by assigning a variable declared outside itself.
 *
 * @remarks
 * `submitTask` dedups by activity id: a second caller for a live id is handed the first run's
 * promise and its own `run` never executes. A variable assigned inside `run` therefore keeps its
 * initial value for that caller, which reads as a successful call that produced nothing.
 *
 * Only an outer variable that is also read after the submission is reported, since that is what
 * makes it the result channel rather than incidental bookkeeping.
 *
 * @example
 * ```ts
 * // Fails: a deduped caller returns the initial {}
 * let details = {};
 * const outcome = await submitTask({ run: async () => { details = await fetch(); } });
 * return details;
 *
 * // Passes: the value rides the outcome
 * const outcome = await submitTask<Details>({ run: async () => ok(await fetch()) });
 * return outcome.value;
 * ```
 */
const noClosureResultInActivityRun = {
  meta: {
    docs: { description: 'take an activity result from its outcome, not from a variable its run assigns' },
    messages: {
      closureResult: 'Result assigned to `{{name}}`, declared outside `run`. A deduped caller never executes `run`, so it reads the initial value. Return the value from `run` and take it from the outcome.',
    },
    schema: [],
    type: 'problem',
  },
  create(context) {
    const { sourceCode } = context;

    /** The `run` property of an object passed directly to one of the submitters. */
    const runBodyOf = (node) => {
      if (node.callee.type !== 'Identifier' || !ACTIVITY_SUBMITTERS.has(node.callee.name))
        return undefined;

      const spec = node.arguments[0];
      if (spec?.type !== 'ObjectExpression')
        return undefined;

      return spec.properties.find(property =>
        property.type === 'Property'
        && property.key.type === 'Identifier'
        && property.key.name === 'run',
      )?.value;
    };

    const isInside = (node, ancestor) => node.range[0] >= ancestor.range[0] && node.range[1] <= ancestor.range[1];

    return {
      CallExpression(node) {
        const run = runBodyOf(node);
        if (!run)
          return;

        const runScope = sourceCode.scopeManager.acquire(run);
        if (!runScope)
          return;

        const reported = new Set();

        const walk = (scope) => {
          for (const reference of scope.references) {
            const variable = reference.resolved;
            if (!reference.isWrite() || !variable || reported.has(variable))
              continue;

            // Declared outside `run`, so the assignment cannot reach a deduped caller.
            if (variable.defs.some(def => isInside(def.name, run)))
              continue;

            const readAfterSubmission = variable.references.some(other =>
              other.isRead() && !isInside(other.identifier, run) && other.identifier.range[0] > node.range[1],
            );
            if (!readAfterSubmission)
              continue;

            reported.add(variable);
            context.report({
              data: { name: variable.name },
              messageId: 'closureResult',
              node: reference.identifier,
            });
          }

          scope.childScopes.forEach(walk);
        };

        walk(runScope);
      },
    };
  },
};

export const localRules = {
  'no-closure-result-in-activity-run': noClosureResultInActivityRun,
};
