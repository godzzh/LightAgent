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

/* 品牌色板（对齐参考项目 Admin 后台：主色 #184cff） */
const BRAND = '#184CFF'
const BRAND_HOVER = '#4770FF'
const BRAND_PRESSED = '#1038D6'
const TEXT = '#1F2329'
const TEXT_2 = '#4E5969'
const BORDER = '#E5EAF3'

const themeOverrides: GlobalThemeOverrides = {
  common: {
    // 品牌色：#184cff
    primaryColor: BRAND,
    primaryColorHover: BRAND_HOVER,
    primaryColorPressed: BRAND_PRESSED,
    primaryColorSuppl: BRAND,

    // 语义色
    infoColor: BRAND,
    successColor: '#34C759',
    warningColor: '#FF9500',
    errorColor: '#FF3B30',

    // 形状：统一 4px 圆角
    borderRadius: '4px',
    borderRadiusSmall: '4px',

    // 文本与描边
    textColorBase: TEXT,
    textColor1: TEXT,
    textColor2: TEXT_2,
    textColor3: '#86909C',
    borderColor: BORDER,
    dividerColor: BORDER,
    placeholderColor: '#86909C',

    // 字体
    fontFamily:
      '-apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", Inter, "PingFang SC", "Helvetica Neue", "Microsoft YaHei", sans-serif',
    fontFamilyMono: '"SF Mono", "JetBrains Mono", Menlo, Consolas, monospace',
    fontSize: '14px',
    fontWeightStrong: '600',

    // 表面层次
    bodyColor: '#F5F7FA',
    cardColor: '#FFFFFF',
    modalColor: '#FFFFFF',
    popoverColor: '#FFFFFF',
    tableColor: '#FFFFFF',
    inputColor: '#FFFFFF',
    hoverColor: 'rgba(24, 76, 255, 0.06)',

    // 阴影：iOS 极轻
    boxShadow1: '0 4px 20px rgba(15,23,42,0.06)',
    boxShadow2: '0 8px 28px rgba(15,23,42,0.10)',
    boxShadow3: '0 24px 70px rgba(15,23,42,0.18)',
  },

  Layout: {
    color: '#F5F7FA',
    siderColor: '#F8F9FF',
  },

  Button: {
    borderRadiusTiny: '4px',
    borderRadiusSmall: '4px',
    borderRadiusMedium: '4px',
    borderRadiusLarge: '4px',
    fontWeight: '500',
    textColorPrimary: '#FFFFFF',
    textColorHoverPrimary: '#FFFFFF',
    textColorPressedPrimary: '#FFFFFF',
    textColorFocusPrimary: '#FFFFFF',
    colorPrimary: BRAND,
    colorHoverPrimary: BRAND_HOVER,
    colorPressedPrimary: BRAND_PRESSED,
    colorFocusPrimary: BRAND_HOVER,
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
    textColor: TEXT,
    textColorHover: TEXT,
    textColorPressed: TEXT,
  },

  Input: {
    borderRadius: '4px',
    heightMedium: '36px',
    heightLarge: '42px',
    color: '#FFFFFF',
    colorFocus: '#FFFFFF',
    border: `1px solid ${BORDER}`,
    borderHover: '1px solid #8EADFF',
    borderFocus: `1px solid ${BRAND}`,
    boxShadowFocus: '0 0 0 3px rgba(24,76,255,0.10)',
    placeholderColor: '#86909C',
  },

  InternalSelection: {
    borderRadius: '4px',
    heightMedium: '36px',
    heightLarge: '42px',
    border: `1px solid ${BORDER}`,
    borderHover: '1px solid #8EADFF',
    borderActive: `1px solid ${BRAND}`,
    borderFocus: `1px solid ${BRAND}`,
    boxShadowActive: '0 0 0 3px rgba(24,76,255,0.10)',
    boxShadowFocus: '0 0 0 3px rgba(24,76,255,0.10)',
  },

  Card: {
    borderRadius: '4px',
    color: '#FFFFFF',
    borderColor: BORDER,
    paddingMedium: '18px',
  },

  DataTable: {
    thColor: '#F7F9FC',
    thTextColor: '#64748B',
    thFontWeight: '500',
    borderRadius: '4px',
    tdColor: '#FFFFFF',
    tdColorHover: '#F8FAFF',
    borderColor: BORDER,
    thPaddingMedium: '10px 14px',
    tdPaddingMedium: '12px 14px',
  },

  Modal: {
    borderRadius: '4px',
  },

  Drawer: {
    borderRadius: '4px 0 0 4px',
  },

  Tag: {
    borderRadius: '999px',
    heightMedium: '22px',
    fontSizeMedium: '12px',
  },

  Tabs: {
    tabFontWeightActive: '600',
    tabFontWeight: '500',
    tabTextColorActiveLine: TEXT,
    barColor: BRAND,
    tabBorderColor: BORDER,
  },

  Switch: {
    // railColorActive 默认取 common.primaryColor；此前硬编码绿色导致与主题不一致。
    // railBorderRadius* / buttonBorderRadius* 默认取 common.borderRadius（4px），
    // 配合模板里的 :round="false" 即为方形轨道。
    railColorActive: BRAND,
    railColor: 'rgba(120,120,128,0.16)',
  },

  Popover: {
    borderRadius: '4px',
    padding: '6px',
  },

  Dropdown: {
    borderRadius: '4px',
    optionHeightMedium: '34px',
    fontSizeMedium: '13.5px',
  },

  Pagination: {
    itemBorderRadius: '4px',
  },

  Message: {
    borderRadius: '4px',
    boxShadow: '0 8px 32px -8px rgba(0,0,0,0.18)',
  },

  Notification: {
    borderRadius: '4px',
  },

  Empty: {
    textColor: TEXT_2,
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
