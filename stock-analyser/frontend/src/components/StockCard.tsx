import React from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity,
  Platform, ViewStyle,
} from 'react-native';
import { Recommendation } from '../types';
import { Colors, Spacing, Radius, Shadow } from '../theme';

interface Props {
  rec: Recommendation;
  onPress: (rec: Recommendation) => void;
}

function scoreColor(score?: number): string {
  if (!score) return Colors.neutral;
  if (score >= 75) return Colors.scoreHigh;
  if (score >= 55) return Colors.scoreMid;
  return Colors.scoreLow;
}

function trendColor(pct?: number): string {
  if (pct === undefined || pct === null) return Colors.textSecondary;
  return pct >= 0 ? Colors.profit : Colors.loss;
}

const fmt = (n?: number, dec = 2): string =>
  n !== undefined && n !== null ? n.toFixed(dec) : '—';

export const StockCard: React.FC<Props> = ({ rec, onPress }) => {
  const sc  = scoreColor(rec.score);
  const rsiColor =
    rec.rsi === undefined ? Colors.neutral
    : rec.rsi >= 70       ? Colors.loss
    : rec.rsi >= 50       ? Colors.profit
    : Colors.warning;

  return (
    <TouchableOpacity
      style={styles.card}
      activeOpacity={0.82}
      onPress={() => onPress(rec)}
    >
      {/* ── Header ── */}
      <View style={styles.header}>
        <View style={styles.rankBadge}>
          <Text style={styles.rankText}>#{rec.rank}</Text>
        </View>

        <View style={{ flex: 1, marginLeft: Spacing.sm }}>
          <Text style={styles.symbol}>{rec.symbol}</Text>
          {rec.company_name ? (
            <Text style={styles.companyName} numberOfLines={1}>{rec.company_name}</Text>
          ) : null}
        </View>

        {/* Score circle */}
        <View style={[styles.scoreBadge, { borderColor: sc }]}>
          <Text style={[styles.scoreText, { color: sc }]}>{rec.score}</Text>
          <Text style={[styles.scoreLabel, { color: sc }]}>score</Text>
        </View>
      </View>

      {/* ── Price Row ── */}
      <View style={styles.priceRow}>
        <PriceBox label="Entry ₹" value={fmt(rec.entry_price)} />
        <PriceBox label="SL ₹"    value={fmt(rec.stop_loss)}   sub={`-${fmt(rec.sl_percentage, 1)}%`} subColor={Colors.loss} />
        <PriceBox label="T1 ₹"    value={fmt(rec.target1)}     sub={`+${fmt(rec.target1_percentage, 1)}%`} subColor={Colors.profit} />
        <PriceBox label="T2 ₹"    value={fmt(rec.target2)}     sub={`+${fmt(rec.target2_percentage, 1)}%`} subColor={Colors.profit} />
      </View>

      {/* ── Indicators Row ── */}
      <View style={styles.indicatorRow}>
        <Indicator label="RSI"  value={fmt(rec.rsi, 1)}       color={rsiColor} />
        <Indicator label="ADX"  value={fmt(rec.adx, 1)}       color={Colors.accent} />
        <Indicator label="Vol×" value={fmt(rec.volume_ratio, 1)} color={rec.volume_ratio && rec.volume_ratio >= 1.5 ? Colors.profit : Colors.textSecondary} />
        {rec.sector ? (
          <View style={styles.sectorPill}>
            <Text style={styles.sectorText} numberOfLines={1}>{rec.sector}</Text>
          </View>
        ) : null}
      </View>
    </TouchableOpacity>
  );
};

const PriceBox: React.FC<{
  label: string; value: string; sub?: string; subColor?: string;
}> = ({ label, value, sub, subColor }) => (
  <View style={styles.priceBox}>
    <Text style={styles.priceLabel}>{label}</Text>
    <Text style={styles.priceValue}>{value}</Text>
    {sub ? <Text style={[styles.priceSub, { color: subColor }]}>{sub}</Text> : null}
  </View>
);

const Indicator: React.FC<{ label: string; value: string; color: string }> = ({
  label, value, color,
}) => (
  <View style={styles.indicatorBox}>
    <Text style={styles.indicatorLabel}>{label}</Text>
    <Text style={[styles.indicatorValue, { color }]}>{value}</Text>
  </View>
);

const styles = StyleSheet.create({
  card: {
    backgroundColor: Colors.card,
    borderRadius: Radius.md,
    marginHorizontal: Spacing.md,
    marginVertical: Spacing.xs,
    padding: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.border,
    ...Shadow.card,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: Spacing.sm,
  },
  rankBadge: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: Colors.primary + '22',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: Colors.primary + '44',
  },
  rankText: {
    color: Colors.primary,
    fontSize: 11,
    fontWeight: '700',
  },
  symbol: {
    color: Colors.textPrimary,
    fontSize: 17,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  companyName: {
    color: Colors.textSecondary,
    fontSize: 12,
    marginTop: 1,
  },
  scoreBadge: {
    width: 52,
    height: 52,
    borderRadius: 26,
    borderWidth: 2,
    alignItems: 'center',
    justifyContent: 'center',
  },
  scoreText: {
    fontSize: 16,
    fontWeight: '800',
  },
  scoreLabel: {
    fontSize: 9,
    fontWeight: '600',
    marginTop: -2,
  },
  priceRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    backgroundColor: Colors.surface,
    borderRadius: Radius.sm,
    paddingVertical: Spacing.sm,
    paddingHorizontal: Spacing.xs,
    marginBottom: Spacing.sm,
  },
  priceBox: {
    flex: 1,
    alignItems: 'center',
  },
  priceLabel: {
    color: Colors.textMuted,
    fontSize: 9,
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  priceValue: {
    color: Colors.textPrimary,
    fontSize: 13,
    fontWeight: '700',
    marginTop: 2,
  },
  priceSub: {
    fontSize: 10,
    fontWeight: '600',
    marginTop: 1,
  },
  indicatorRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
  },
  indicatorBox: {
    alignItems: 'center',
    backgroundColor: Colors.surface,
    borderRadius: Radius.sm,
    paddingHorizontal: Spacing.sm,
    paddingVertical: 4,
  },
  indicatorLabel: {
    color: Colors.textMuted,
    fontSize: 9,
    fontWeight: '600',
    textTransform: 'uppercase',
  },
  indicatorValue: {
    fontSize: 13,
    fontWeight: '700',
    marginTop: 1,
  },
  sectorPill: {
    flex: 1,
    backgroundColor: Colors.accent + '20',
    borderRadius: Radius.full,
    paddingHorizontal: Spacing.sm,
    paddingVertical: 3,
    alignSelf: 'center',
  },
  sectorText: {
    color: Colors.accent,
    fontSize: 10,
    fontWeight: '600',
    textAlign: 'center',
  },
});
