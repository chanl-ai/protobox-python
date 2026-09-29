import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

const eslintConfig = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    rules: {
      // Warn about console statements (except error and warn)
      "no-console": ["warn", { 
        allow: ["warn", "error", "time", "timeEnd", "table", "group", "groupEnd"] 
      }],
      
      // Error on debugger statements
      "no-debugger": "error",
      
      // Warn about unused variables (helps catch debug code)
      "@typescript-eslint/no-unused-vars": ["warn", {
        argsIgnorePattern: "^_",
        varsIgnorePattern: "^_",
        caughtErrorsIgnorePattern: "^_"
      }],
      
      // Custom rule to suggest using logger instead of console
      "no-restricted-syntax": [
        "warn",
        {
          selector: "CallExpression[callee.object.name='console'][callee.property.name='log']",
          message: "Use logger.debug() or logger.info() instead of console.log()"
        },
        {
          selector: "CallExpression[callee.object.name='console'][callee.property.name='debug']",
          message: "Use logger.debug() instead of console.debug()"
        }
      ],
      
      // Ban imports from deprecated client.ts (except type imports for backward compatibility)
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            {
              group: ["@/lib/api/client"],
              message: "Import types from '@/lib/api/client-types' or '@/lib/api/hooks' instead. client.ts is deprecated.",
              allowTypeImports: true // Allow type-only imports for backward compatibility
            },
            {
              group: ["@/components/workspace-provider"],
              message: "WorkspaceProvider has been removed. Use useAuthStore() from '@/lib/auth/stores/auth.store' instead."
            }
          ]
        }
      ]
    },
    
    // Override rules for specific files
    overrides: [
      {
        // Allow console in logger implementation
        files: ["lib/logger.ts", "lib/logger/*.ts"],
        rules: {
          "no-console": "off",
          "no-restricted-syntax": "off"
        }
      },
      {
        // Allow console in debug utilities
        files: ["lib/debug/**/*.ts", "lib/debug/**/*.tsx"],
        rules: {
          "no-console": "off",
          "no-restricted-syntax": "off"
        }
      },
      {
        // Stricter rules for production code
        files: ["app/**/*.tsx", "components/**/*.tsx"],
        rules: {
          "no-console": "error",
          "no-debugger": "error"
        }
      }
    ]
  }
];

export default eslintConfig;
