import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{js,jsx}'],
    extends: [
      js.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    rules: {
      // `catch {}` on best-effort fetches is an established pattern here
      'no-empty': ['error', { allowEmptyCatch: true }],
      // React-Compiler-era rules from eslint-plugin-react-hooks v7. The code
      // predates them; they flag patterns to migrate away from, not bugs.
      // Warnings for now — tracked cleanup, don't let them block CI.
      'react-hooks/set-state-in-effect': 'warn',
      'react-hooks/immutability': 'warn',
      'react-hooks/purity': 'warn',
      // AuthContext intentionally exports the useAuth hook alongside the provider
      'react-refresh/only-export-components': ['warn', { allowExportNames: ['useAuth'] }],
    },
  },
])
