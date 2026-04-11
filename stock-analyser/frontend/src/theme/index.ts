// Theme — dark financial dashboard palette

export const Colors = {
  // Backgrounds
  background:    '#0F1923',
  surface:       '#1A2735',
  card:          '#1E2F3E',
  cardHover:     '#243547',
  border:        '#2A3F52',

  // Text
  textPrimary:   '#F0F4F8',
  textSecondary: '#8BA3B8',
  textMuted:     '#546E7A',

  // Accents
  primary:       '#00C896',    // teal-green — buy signal
  primaryDark:   '#009F78',
  accent:        '#2196F3',    // blue — general accent

  // Semantic
  profit:        '#00E676',    // bright green
  loss:          '#FF5252',    // red
  warning:       '#FFB300',    // amber
  info:          '#03A9F4',    // light blue
  neutral:       '#8BA3B8',

  // Trend
  bullish:       '#00C896',
  bearish:       '#FF5252',

  // Score bands
  scoreHigh:     '#00C896',    // ≥ 75
  scoreMid:      '#FFB300',    // 50-74
  scoreLow:      '#FF5252',    // < 50

  // Score bar gradient
  gradient1:     '#00C896',
  gradient2:     '#1E88E5',
};

export const Fonts = {
  regular:   'System',
  medium:    'System',
  bold:      'System',
  mono:      Platform.OS === 'ios' ? 'Courier New' : 'monospace',
};

// Tiny helper — import Platform where used
import { Platform } from 'react-native';

export const Spacing = {
  xs:  4,
  sm:  8,
  md:  16,
  lg:  24,
  xl:  32,
  xxl: 48,
};

export const Radius = {
  sm:  6,
  md:  12,
  lg:  18,
  xl:  24,
  full: 999,
};

export const Shadow = {
  card: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 6,
  },
};
