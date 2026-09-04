// ESLint flat config for the OCR frontend (Vue 3 + Vite).
// Baseline is lenient on purpose: the codebase predates the linter, so
// rules that would flood on existing components start as "off" or "warn".
// Tighten individual rules as the violations get cleaned up.
// CommonJS on purpose: package.json has no "type": "module".

const js = require('@eslint/js');
const pluginVue = require('eslint-plugin-vue');
const globals = require('globals');

module.exports = [
  {
    ignores: [
      'dist/**',
      'node_modules/**',
      'wiki/**',
      'binaries/**',
      'public/**',
    ],
  },

  js.configs.recommended,

  // vue/essential catches real errors (bad v-for keys, duplicate attrs,
  // unused components) without the stylistic churn of flat/recommended.
  ...pluginVue.configs['flat/essential'],

  {
    files: ['**/*.js', '**/*.vue'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: {
        ...globals.browser,
      },
    },
    rules: {
      // View components use single-word route names (Course.vue, Labs.vue).
      'vue/multi-word-component-names': 'off',
      // Legacy code keeps some vars around for readability; warn, do not fail.
      'no-unused-vars': ['warn', { args: 'none' }],
      'vue/no-unused-vars': 'warn',
      // console.* is used for operator-facing diagnostics in the SPA.
      'no-console': 'off',
      // Legacy code swallows errors with empty catch blocks in 16 places;
      // allow that pattern, still flag other empty blocks.
      'no-empty': ['error', { allowEmptyCatch: true }],
    },
  },

  // Build tooling runs in Node, not the browser. Vite pre-bundles its
  // config as ESM; this file itself is CommonJS.
  {
    files: ['vite.config.js'],
    languageOptions: {
      globals: {
        ...globals.node,
      },
    },
  },
  {
    files: ['eslint.config.js'],
    languageOptions: {
      sourceType: 'commonjs',
      globals: {
        ...globals.node,
      },
    },
  },
];
