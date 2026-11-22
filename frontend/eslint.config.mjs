import { defineConfig, globalIgnores } from 'eslint/config';
import nextVitals from 'eslint-config-next/core-web-vitals';
import nextTs from 'eslint-config-next/typescript';

export default defineConfig([
  nextVitals,
  nextTs,
  {
    rules: {
      // Existing dashboard uses dynamic API payloads; keep these visible as warnings
      // while blocking all other lint errors in CI.
      '@typescript-eslint/no-explicit-any': 'warn',
    },
  },
  globalIgnores(['.next/**', 'out/**', 'build/**', 'next-env.d.ts']),
]);
