module.exports = {
  plugins: {
    '@tailwindcss/postcss': {
      // 禁用 oklab 颜色空间，使用传统的 rgb/hsl
      // 这样可以避免 html2canvas 兼容性问题
      optimize: {
        minify: true,
      },
    },
  },
}
