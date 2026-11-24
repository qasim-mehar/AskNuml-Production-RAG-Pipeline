import { fileURLToPath } from "node:url";

import { defineConfig } from "vitest/config";

/** Web test config: jsdom DOM, stable aliases, MSW-equivalent fetch mocks. */
export default defineConfig({
  esbuild: { jsx: "automatic", jsxImportSource: "react" },
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
  },
});
