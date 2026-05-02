import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [tailwindcss()],
  server: {
    port: 5174,
    host: "0.0.0.0",
    allowedHosts: [".manus.computer"],
  },
});
