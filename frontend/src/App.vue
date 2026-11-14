<script setup lang="ts">
import {
  NConfigProvider,
  NMessageProvider,
  NDialogProvider,
  NNotificationProvider,
  zhCN,
  dateZhCN,
  type GlobalThemeOverrides,
} from 'naive-ui'
import { RouterView } from 'vue-router'

/* iOS 系统色板（HIG 明色模式） */
const IOS_BLUE = '#007AFF'
const IOS_TEXT = '#1C1C1E'
const IOS_TEXT_2 = 'rgba(60, 60, 67, 0.6)'
const IOS_SEPARATOR = 'rgba(60, 60, 67, 0.13)'
const IOS_FILL = 'rgba(118, 118, 128, 0.08)'

const themeOverrides: GlobalThemeOverrides = {
  common: {
    // 品牌色：iOS 系统蓝
    primaryColor: IOS_BLUE,
    primaryColorHover: '#3395FF',
    primaryColorPressed: '#0062CC',
    primaryColorSuppl: IOS_BLUE,

    // 语义色
    infoColor: IOS_BLUE,
    successColor: '#34C759',
    warningColor: '#FF9500',
    errorColor: '#FF3B30',

    // 形状：iOS 连续圆角
    borderRadius: '10px',
    borderRadiusSmall: '8px',

    // 文本与描边
    textColorBase: IOS_TEXT,
    textColor1: IOS_TEXT,
    textColor2: IOS_TEXT_2,
    textColor3: 'rgba(60, 60, 67, 0.38)',
    borderColor: IOS_SEPARATOR,
    dividerColor: IOS_SEPARATOR,
    placeholderColor: 'rgba(60, 60, 67, 0.38)',

    // 字体
    fontFamily:
      '-apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", Inter, "PingFang SC", "Helvetica Neue", "Microsoft YaHei", sans-serif',
    fontFamilyMono: '"SF Mono", "JetBrains Mono", Menlo, Consolas, monospace',
    fontSize: '14px',
    fontWeightStrong: '600',

    // 表面层次
    bodyColor: '#F2F2F7',
    cardColor: '#FFFFFF',
    modalColor: '#FFFFFF',
    popoverColor: '#FFFFFF',
    tableColor: '#FFFFFF',
    inputColor: '#FFFFFF',
    hoverColor: 'rgba(120, 120, 128, 0.08)',

    // 阴影：iOS 极轻
    boxShadow1: '0 1px 2px rgba(0,0,0,0.04), 0 8px 24px -12px rgba(0,0,0,0.10)',
    boxShadow2: '0 4px 12px rgba(0,0,0,0.08), 0 16px 40px -16px rgba(0,0,0,0.16)',
    boxShadow3: '0 8px 32px -8px rgba(0,0,0,0.18)',
  },

  Layout: {
    color: '#F2F2F7',
    siderColor: 'rgba(255,255,255,0.72)',
  },

  Button: {
    borderRadiusTiny: '8px',
    borderRadiusSmall: '9px',
    borderRadiusMedium: '10px',
    borderRadiusLarge: '12px',
    fontWeight: '500',
    textColorPrimary: '#FFFFFF',
    textColorHoverPrimary: '#FFFFFF',
    textColorPressedPrimary: '#FFFFFF',
    textColorFocusPrimary: '#FFFFFF',
    colorPrimary: IOS_BLUE,
    colorHoverPrimary: '#3395FF',
    colorPressedPrimary: '#0062CC',
    colorFocusPrimary: '#3395FF',
    borderPrimary: '1px solid transparent',
    borderHoverPrimary: '1px solid transparent',
    borderPressedPrimary: '1px solid transparent',
    borderFocusPrimary: '1px solid transparent',
    // 默认按钮：iOS 浅灰填充
    color: '#FFFFFF',
    colorHover: '#F5F5F7',
    colorPressed: '#EBEBF0',
    border: '1px solid rgba(60,60,67,0.13)',
    borderHover: '1px solid rgba(60,60,67,0.18)',
    borderPressed: '1px solid rgba(60,60,67,0.22)',
    textColor: IOS_TEXT,
    textColorHover: IOS_TEXT,
    textColorPressed: IOS_TEXT,
  },

  Input: {
    borderRadius: '10px',
    heightMedium: '36px',
    heightLarge: '42px',
    color: '#FFFFFF',
    colorFocus: '#FFFFFF',
    border: `1px solid ${IOS_SEPARATOR}`,
    borderHover: '1px solid rgba(0,122,255,0.45)',
    borderFocus: `1px solid ${IOS_BLUE}`,
    boxShadowFocus: '0 0 0 3px rgba(0,122,255,0.16)',
    placeholderColor: 'rgba(60,60,67,0.38)',
  },

  InternalSelection: {
    borderRadius: '10px',
    heightMedium: '36px',
    heightLarge: '42px',
    border: `1px solid ${IOS_SEPARATOR}`,
    borderHover: '1px solid rgba(0,122,255,0.45)',
    borderActive: `1px solid ${IOS_BLUE}`,
    borderFocus: `1px solid ${IOS_BLUE}`,
    boxShadowActive: '0 0 0 3px rgba(0,122,255,0.16)',
    boxShadowFocus: '0 0 0 3px rgba(0,122,255,0.16)',
  },

  Card: {
    borderRadius: '18px',
    color: '#FFFFFF',
    borderColor: 'rgba(0,0,0,0.03)',
    paddingMedium: '18px',
  },

  DataTable: {
    thColor: 'transparent',
    thTextColor: IOS_TEXT_2,
    thFontWeight: '500',
    borderRadius: '18px',
    tdColor: '#FFFFFF',
    tdColorHover: 'rgba(120,120,128,0.06)',
    borderColor: IOS_SEPARATOR,
    thPaddingMedium: '10px 14px',
    tdPaddingMedium: '12px 14px',
  },

  Modal: {
    borderRadius: '20px',
  },

  Drawer: {
    borderRadius: '20px 0 0 20px',
  },

  Tag: {
    borderRadius: '999px',
    heightMedium: '22px',
    fontSizeMedium: '12px',
  },

  Tabs: {
    tabFontWeightActive: '600',
    tabFontWeight: '500',
    tabTextColorActiveLine: IOS_TEXT,
    barColor: IOS_BLUE,
    tabBorderColor: IOS_SEPARATOR,
  },

  Switch: {
    railColorActive: '#34C759',
    railColor: 'rgba(120,120,128,0.16)',
  },

  Popover: {
    borderRadius: '14px',
    padding: '6px',
  },

  Dropdown: {
    borderRadius: '14px',
    optionHeightMedium: '34px',
    fontSizeMedium: '13.5px',
  },

  Pagination: {
    itemBorderRadius: '8px',
  },

  Message: {
    borderRadius: '14px',
    boxShadow: '0 8px 32px -8px rgba(0,0,0,0.18)',
  },

  Notification: {
    borderRadius: '16px',
  },

  Empty: {
    textColor: IOS_TEXT_2,
  },
}
</script>

<template>
  <NConfigProvider :theme-overrides="themeOverrides" :locale="zhCN" :date-locale="dateZhCN">
    <NMessageProvider>
      <NDialogProvider>
        <NNotificationProvider>
          <RouterView />
        </NNotificationProvider>
      </NDialogProvider>
    </NMessageProvider>
  </NConfigProvider>
</template>
