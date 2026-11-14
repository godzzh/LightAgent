/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // iOS 系统色（Human Interface Guidelines 明色模式）
        primary: '#007AFF',
        'primary-press': '#0062CC',
        surface: '#F2F2F7', // systemGroupedBackground
        elevated: '#FFFFFF', // secondarySystemGroupedBackground
        ink: '#1C1C1E', // label
        muted: '#8E8E93', // secondaryLabel
        line: 'rgba(60,60,67,0.13)', // separator
        success: '#34C759',
        warning: '#FF9500',
        danger: '#FF3B30',
        teal: '#30B0C7',
        indigo: '#5856D6',
        purple: '#AF52DE',
      },
      fontFamily: {
        sans: [
          '-apple-system',
          'BlinkMacSystemFont',
          'SF Pro Text',
          'SF Pro Display',
          'Inter',
          'PingFang SC',
          'Helvetica Neue',
          'Microsoft YaHei',
          'sans-serif',
        ],
        mono: ['SF Mono', 'JetBrains Mono', 'Menlo', 'Consolas', 'monospace'],
      },
      borderRadius: {
        // iOS 连续圆角近似值
        card: '18px',
        group: '12px',
        control: '10px',
      },
      boxShadow: {
        // 极轻阴影：iOS 靠层次与留白，而非重投影
        card: '0 1px 2px rgba(0,0,0,0.04), 0 8px 24px -12px rgba(0,0,0,0.10)',
        float: '0 4px 12px rgba(0,0,0,0.08), 0 16px 40px -16px rgba(0,0,0,0.16)',
        press: 'inset 0 1px 2px rgba(0,0,0,0.06)',
      },
      transitionTimingFunction: {
        // iOS 弹簧近似曲线
        ios: 'cubic-bezier(0.32, 0.72, 0, 1)',
      },
      spacing: {
        4.5: '1.125rem',
        13: '3.25rem',
      },
    },
  },
  plugins: [],
}
