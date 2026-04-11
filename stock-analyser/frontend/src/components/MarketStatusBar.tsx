import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { MarketStatus } from '../types';
import { Colors, Spacing, Radius } from '../theme';

interface Props {
  status?: MarketStatus;
}

export const MarketStatusBar: React.FC<Props> = ({ status }) => {
  if (!status) {
    return (
      <View style={[styles.bar, { backgroundColor: Colors.surface }]}>
        <Text style={styles.statusText}>Fetching market status…</Text>
      </View>
    );
  }

  const isOpen = status.is_open;
  const barColor = isOpen ? Colors.profit + '22' : Colors.surface;
  const dotColor = isOpen ? Colors.profit : Colors.textMuted;

  const trendColor =
    status.nifty_trend === 'bullish' ? Colors.bullish
    : status.nifty_trend === 'bearish' ? Colors.bearish
    : Colors.neutral;

  const changeColor =
    (status.nifty_change_pct ?? 0) >= 0 ? Colors.profit : Colors.loss;

  return (
    <View style={[styles.bar, { backgroundColor: barColor, borderColor: dotColor + '44' }]}>
      {/* Status dot + label */}
      <View style={styles.leftSection}>
        <View style={[styles.dot, { backgroundColor: dotColor }]} />
        <Text style={[styles.statusText, { color: dotColor }]}>{status.status}</Text>
      </View>

      {/* NIFTY data */}
      {status.nifty_last_close ? (
        <View style={styles.niftySection}>
          <Text style={styles.niftyLabel}>NIFTY 50</Text>
          <Text style={styles.niftyValue}>
            {status.nifty_last_close.toFixed(2)}
          </Text>
          {status.nifty_change_pct !== undefined ? (
            <Text style={[styles.niftyChange, { color: changeColor }]}>
              {status.nifty_change_pct >= 0 ? '+' : ''}
              {status.nifty_change_pct.toFixed(2)}%
            </Text>
          ) : null}
        </View>
      ) : null}

      {/* Trend pill */}
      {status.nifty_trend ? (
        <View style={[styles.trendPill, { borderColor: trendColor + '66', backgroundColor: trendColor + '22' }]}>
          <Text style={[styles.trendText, { color: trendColor }]}>
            {status.nifty_trend.toUpperCase()}
          </Text>
        </View>
      ) : null}

      {/* Time */}
      <Text style={styles.timeText}>{status.current_time_ist?.slice(11, 16)} IST</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  bar: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    borderBottomWidth: 1,
    gap: Spacing.sm,
  },
  leftSection: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  statusText: {
    color: Colors.textSecondary,
    fontSize: 12,
    fontWeight: '600',
  },
  niftySection: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    flex: 1,
    justifyContent: 'center',
  },
  niftyLabel: {
    color: Colors.textMuted,
    fontSize: 11,
    fontWeight: '600',
  },
  niftyValue: {
    color: Colors.textPrimary,
    fontSize: 13,
    fontWeight: '700',
  },
  niftyChange: {
    fontSize: 12,
    fontWeight: '700',
  },
  trendPill: {
    borderRadius: Radius.full,
    borderWidth: 1,
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
  trendText: {
    fontSize: 9,
    fontWeight: '800',
    letterSpacing: 0.5,
  },
  timeText: {
    color: Colors.textMuted,
    fontSize: 10,
    fontWeight: '500',
  },
});
