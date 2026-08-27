/**
 * Local ESLint rules for this workspace, registered under the `local/` plugin namespace in
 * `eslint.config.js`.
 *
 * @packageDocumentation
 */

/**
 * Matches a `//` comment carrying a directive rather than prose.
 *
 * @remarks
 * Directives stack legitimately: silencing two rules on one line needs two of them, and a
 * `@ts-expect-error` may sit alongside one.
 */
const DIRECTIVE_COMMENT = /^\s*(?:eslint-|@ts-(?:expect-error|ignore|nocheck)|prettier-|[cv]8 ignore|istanbul )/;

/** The declaration node types that take TSDoc, mapped to the noun a report calls each one. */
const DECLARATION_KINDS = {
  ClassDeclaration: 'class',
  FunctionDeclaration: 'function',
  MethodDefinition: 'method',
  TSDeclareFunction: 'function',
  TSEnumDeclaration: 'enum',
  TSInterfaceDeclaration: 'interface',
  TSModuleDeclaration: 'module',
  TSTypeAliasDeclaration: 'type',
};

/**
 * Collects the `//` comments directly above a node, in source order.
 *
 * @remarks
 * Walks upwards from the node and stops at the first line that is not an adjacent `//` comment, so
 * a blank line ends the run. Stops at a directive as well, which is aimed at the code below rather
 * than documenting it. Reads through an `export`, where the comment attaches to the export rather
 * than to the declaration inside it.
 *
 * @param sourceCode - the rule context's source code object
 * @param node - the declaration to look above
 * @returns the adjacent comments, nearest to the node last, or an empty array
 */
function attachedLineComments(sourceCode, node) {
  const exported = node.parent?.type === 'ExportNamedDeclaration' || node.parent?.type === 'ExportDefaultDeclaration';
  const target = exported ? node.parent : node;

  const attached = [];
  let line = target.loc.start.line;
  for (const comment of sourceCode.getCommentsBefore(target).slice().reverse()) {
    if (comment.type !== 'Line' || comment.loc.end.line !== line - 1 || DIRECTIVE_COMMENT.test(comment.value))
      break;
    attached.unshift(comment);
    line = comment.loc.start.line;
  }
  return attached;
}

/**
 * Disallows two or more consecutive `//` comment lines.
 *
 * @remarks
 * A single `//` line is allowed. A run made entirely of directives is allowed, so several
 * suppressions may be stacked above the line they apply to; a run that mixes a directive with prose
 * is reported.
 *
 * Not autofixable: the replacement depends on what the comment says. Documentation of the code below
 * becomes a TSDoc block, a justified value becomes a named constant, a claim about behaviour becomes
 * an assertion or a test name.
 *
 * @example
 * ```ts
 * // Correct: one line.
 * const timeout = 5000;
 *
 * // eslint-disable-next-line ts/no-unsafe-call -- the shape is checked below
 * // eslint-disable-next-line ts/no-explicit-any -- ditto
 * handler(payload);
 * ```
 *
 * @example
 * ```ts
 * // Incorrect: two lines of prose.
 * // The second line is what makes this a run.
 * const timeout = 5000;
 * ```
 */
const noCommentRun = {
  meta: {
    type: 'suggestion',
    docs: { description: 'disallow consecutive `//` comment lines' },
    messages: {
      run: 'Consecutive `//` lines ({{count}}). Put it in the enclosing declaration\'s TSDoc, encode it as a name or an assertion, or cut it to one line.',
    },
    schema: [],
  },
  create(context) {
    const { sourceCode } = context;

    return {
      'Program:exit': () => {
        let run = [];

        const flush = () => {
          if (run.length >= 2 && !run.every(comment => DIRECTIVE_COMMENT.test(comment.value))) {
            context.report({
              data: { count: run.length },
              loc: { end: run.at(-1).loc.end, start: run[0].loc.start },
              messageId: 'run',
            });
          }
          run = [];
        };

        for (const comment of sourceCode.getAllComments()) {
          if (comment.type !== 'Line')
            continue;

          const previous = run.at(-1);
          const contiguous = previous
            && comment.loc.start.line === previous.loc.end.line + 1
            && comment.loc.start.column === previous.loc.start.column;

          if (!contiguous)
            flush();
          run.push(comment);
        }
        flush();
      },
    };
  },
};

/**
 * Requires a declaration's documentation to be a TSDoc block rather than `//` comments.
 *
 * @remarks
 * Applies to classes, functions, methods, interfaces, type aliases, enums, ambient modules, and a
 * `const` holding a function. Other variable declarations are not covered, so a single `//` line may
 * still introduce a value.
 *
 * Only a `/** *\/` block is surfaced by editors at the call site and checked by the `jsdoc` and
 * `tsdoc` rules, so documentation written as `//` reaches neither.
 *
 * @example
 * ```ts
 * // Incorrect.
 * // Returns the display name for an account.
 * function accountLabel(account: Account): string {}
 * ```
 *
 * @example
 * ```ts
 * // Correct.
 * /** Returns the display name for an account. *\/
 * function accountLabel(account: Account): string {}
 * ```
 */
const tsdocOnDeclaration = {
  meta: {
    type: 'suggestion',
    docs: { description: 'document a declaration with TSDoc rather than `//`' },
    messages: {
      useTsdoc: 'Document this {{kind}} with a TSDoc block (/** ... */), not `//`.',
    },
    schema: [],
  },
  create(context) {
    const { sourceCode } = context;

    const check = (node, kind) => {
      const [first] = attachedLineComments(sourceCode, node);
      if (first)
        context.report({ data: { kind }, loc: first.loc, messageId: 'useTsdoc' });
    };

    const visitors = Object.fromEntries(
      Object.entries(DECLARATION_KINDS).map(([type, kind]) => [type, node => check(node, kind)]),
    );

    return {
      ...visitors,
      VariableDeclaration: (node) => {
        const init = node.declarations.length === 1 ? node.declarations[0].init : undefined;
        if (init && ['ArrowFunctionExpression', 'FunctionExpression'].includes(init.type))
          check(node, 'function');
      },
    };
  },
};

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
  'no-comment-run': noCommentRun,
  'tsdoc-on-declaration': tsdocOnDeclaration,
};
