import type { NextConfig } from "next";

// const nextConfig: NextConfig = {
//  output: 'export',
//   distDir: 'out',
// };
const nextConfig: NextConfig = {
  output: "export",
  distDir: "out",
  outputFileTracingRoot: __dirname,
};

export default nextConfig;
