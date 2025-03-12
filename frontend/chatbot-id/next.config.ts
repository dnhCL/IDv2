import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  eslint: {
    ignoreDuringBuilds: true, // Ignora errores y advertencias de ESLint durante la compilación
  },

};

export default nextConfig;
