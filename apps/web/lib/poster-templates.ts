// 海报模板配置

export interface PosterTemplate {
  id: string;
  name: string;
  thumbnail: string;
  layout: 'simple' | 'wuxing' | 'card';
  style: {
    background: string;
    primaryColor: string;
    secondaryColor: string;
    fontFamily: string;
    accentColor?: string;
  };
}

// 配色主题
export interface ColorTheme {
  name: string;
  primary: string;
  secondary: string;
  background: string;
  text: string;
  accentColor?: string;
}

// 五行配色主题
export const WUXING_THEMES: Record<string, ColorTheme> = {
  fire: {
    name: '火',
    primary: '#FF6B6B',
    secondary: '#FF8E53',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    text: '#FFFFFF',
    accentColor: '#FF6B6B',
  },
  wood: {
    name: '木',
    primary: '#4ADE80',
    secondary: '#22D3EE',
    background: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)',
    text: '#FFFFFF',
    accentColor: '#4ADE80',
  },
  earth: {
    name: '土',
    primary: '#FCD34D',
    secondary: '#F59E0B',
    background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
    text: '#FFFFFF',
    accentColor: '#F59E0B',
  },
  metal: {
    name: '金',
    primary: '#F3F4F6',
    secondary: '#D1D5DB',
    background: 'linear-gradient(135deg, #434343 0%, #000000 100%)',
    text: '#FFFFFF',
    accentColor: '#F3F4F6',
  },
  water: {
    name: '水',
    primary: '#60A5FA',
    secondary: '#3B82F6',
    background: 'linear-gradient(135deg, #0575E6 0%, #021B79 100%)',
    text: '#FFFFFF',
    accentColor: '#60A5FA',
  },
};

// 海报模板列表
export const POSTER_TEMPLATES: PosterTemplate[] = [
  {
    id: 'simple',
    name: '简约风格',
    thumbnail: '/poster/templates/simple.png',
    layout: 'simple',
    style: {
      background: '#FFFFFF',
      primaryColor: '#1F2937',
      secondaryColor: '#6B7280',
      fontFamily: 'PingFang SC, Microsoft YaHei, sans-serif',
    },
  },
  {
    id: 'wuxing',
    name: '五行风格',
    thumbnail: '/poster/templates/wuxing.png',
    layout: 'wuxing',
    style: {
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      primaryColor: '#FFFFFF',
      secondaryColor: '#FCD34D',
      fontFamily: 'STSong, SimSun, serif',
      accentColor: '#FF6B6B',
    },
  },
  {
    id: 'card',
    name: '卡片风格',
    thumbnail: '/poster/templates/card.png',
    layout: 'card',
    style: {
      background: '#F3F4F6',
      primaryColor: '#1F2937',
      secondaryColor: '#6B7280',
      fontFamily: 'PingFang SC, Microsoft YaHei, sans-serif',
    },
  },
];

// 默认模板
export const DEFAULT_TEMPLATE = POSTER_TEMPLATES[0];

// 默认配色主题
export const DEFAULT_THEME = WUXING_THEMES.fire;
