import React from 'react';
import {
  View, Text, ScrollView, StyleSheet,
  ActivityIndicator, TouchableOpacity, Linking,
} from 'react-native';
import { useQuery } from '@tanstack/react-query';
import { Ionicons } from '@expo/vector-icons';
import { getStockAnalysis } from '../services/api';
import { Colors, Spacing, Radius, Shadow } from '../theme';
import { Recommendation, StockAnalysis } from '../types';

interface Props {
  route: { params: { symbol: string; rec?: Recommendation } };
  navigation: any;
}

const fmt = (n?: number | null, dec = 2, prefix = '₹'): string => {
  if (n === undefined || n === null) return '—';
  return `${prefix}${n.toFixed(dec)}`;
};

const fmtPct = (n?: number | null): string => {
  if (n === undefined || n === null) return '—';
  return `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`;
};

export const StockDetailScreen: React.FC<Props> = ({ route, navigation }) => {
  const { symbol, rec: cachedRec } = route.params;

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['stock', symbol],
    queryFn: () => getStockAnalysis(symbol),
    staleTime: 5 * 60 * 1000,
    initialData: cachedRec as StockAnalysis | undefined,
  });

  const stock = data;

  const scoreColor =
    !stock?.score    ? Colors.neutral
    : stock.score >= 75 ? Colors.scoreHigh
    : stock.score >= 55 ? Colors.scoreMid
    : Colors.scoreLow;

  if (isLoading && !cachedRec) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={Colors.primary} />
        <Text style={styles.loadingText}>Analysing {symbol}…</Text>
      </View>
    );
  }

  if (isError && !stock) {
    return (
      <View style={styles.centered}>
        <Ionicons name="alert-circle-outline" size={44} color={Colors.loss} />
        <Text style={styles.errorText}>Failed to load {symbol}</Text>
        <TouchableOpacity onPress={() => refetch()}>
          <Text style={styles.retryText}>Retry</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ paddingBottom: 80 }}>
      {/* ── Hero ──────────────────────────────────────────────────────── */}
      <View style={styles.hero}>
        <View style={{ flex: 1 }}>
          <Text style={styles.heroSymbol}>{symbol}</Text>
          {stock?.company_name ? (
            <Text style={styles.heroName}>{stock.company_name}</Text>
          ) : null}
          {stock?.sector ? (
            <View style={styles.sectorPill}>
              <Text style={styles.sectorText}>{stock.sector}</Text>
            </View>
          ) : null}
        </View>
        <View style={[styles.scoreCircle, { borderColor: scoreColor }]}>
          <Text style={[styles.scoreNum, { color: scoreColor }]}>{stock?.score ?? '—'}</Text>
          <Text style={[styles.scoreLabel, { color: scoreColor }]}>SCORE</Text>
        </View>
      </View>

      {/* ── Entry / Risk ──────────────────────────────────────────────── */}
      <SectionCard title="Trade Setup">
        <View style={styles.tradeGrid}>
          <TradeBox
            label="Entry Price"
            value={fmt(stock?.entry_price)}
            subtitle="Near previous close"
            color={Colors.primary}
          />
          <TradeBox
            label="Stop Loss"
            value={fmt(stock?.stop_loss)}
            subtitle={stock?.sl_percentage ? `-${stock.sl_percentage.toFixed(1)}%` : undefined}
            color={Colors.loss}
          />
        </View>
        <View style={[styles.tradeGrid, { marginTop: Spacing.sm }]}>
          <TradeBox
            label="Target 1  (1:1.5)"
            value={fmt(stock?.target1)}
            subtitle={stock?.target1_percentage ? `+${stock.target1_percentage.toFixed(1)}%` : undefined}
            color={Colors.profit}
          />
          <TradeBox
            label="Target 2  (1:2.5)"
            value={fmt(stock?.target2)}
            subtitle={stock?.target2_percentage ? `+${stock.target2_percentage.toFixed(1)}%` : undefined}
            color={Colors.profit}
          />
        </View>
        <View style={styles.noteBox}>
          <Ionicons name="information-circle-outline" size={14} color={Colors.warning} />
          <Text style={styles.noteText}>
            Square off all positions before 3:25 PM IST. Entry price is approximate (prev close).
          </Text>
        </View>
      </SectionCard>

      {/* ── Technical Indicators ─────────────────────────────────────── */}
      <SectionCard title="Technical Indicators">
        <View style={styles.indicatorGrid}>
          <IndBox label="RSI (14)"      value={stock?.rsi?.toFixed(1)}    unit="" />
          <IndBox label="MACD"          value={stock?.macd?.toFixed(3)}   unit="" />
          <IndBox label="ADX (14)"      value={stock?.adx?.toFixed(1)}    unit="" />
          <IndBox label="Volume Ratio"  value={stock?.volume_ratio?.toFixed(2)} unit="×" />
          <IndBox label="EMA (9)"       value={fmt(stock?.ema9)}     unit="" />
          <IndBox label="EMA (21)"      value={fmt(stock?.ema21)}    unit="" />
          <IndBox label="EMA (50)"      value={fmt(stock?.ema50)}    unit="" />
          <IndBox label="ATR (14)"      value={fmt(stock?.['atr' as keyof StockAnalysis] as number, 2)} unit="" />
        </View>

        {/* Candlestick patterns */}
        {stock?.patterns && stock.patterns.length > 0 && (
          <View style={styles.patternContainer}>
            <Text style={styles.patternTitle}>Detected Patterns</Text>
            <View style={styles.patternRow}>
              {stock.patterns.map((p) => (
                <View key={p} style={styles.patternPill}>
                  <Text style={styles.patternText}>{p.replace(/_/g, ' ').toUpperCase()}</Text>
                </View>
              ))}
            </View>
          </View>
        )}
      </SectionCard>

      {/* ── Price Context ─────────────────────────────────────────────── */}
      <SectionCard title="Price Context">
        <View style={styles.indicatorGrid}>
          <IndBox label="1-Day Change"  value={fmtPct(stock?.pct_change_1d)}  unit="" />
          <IndBox label="5-Day Change"  value={fmtPct(stock?.pct_change_5d)}  unit="" />
          <IndBox label="52W High"      value={fmt(stock?.week52_high)}        unit="" />
          <IndBox label="52W Low"       value={fmt(stock?.week52_low)}         unit="" />
          <IndBox label="PE Ratio"      value={stock?.pe_ratio?.toFixed(1) ?? '—'}   unit="×" />
          <IndBox label="Market Cap"    value={stock?.market_cap_cr ? `₹${stock.market_cap_cr.toLocaleString('en-IN')} Cr` : '—'} unit="" />
        </View>
      </SectionCard>

      {/* ── Analysis Reasons ─────────────────────────────────────────── */}
      {stock?.reasons && stock.reasons.length > 0 && (
        <SectionCard title="Why This Stock">
          {stock.reasons.map((reason, i) => (
            <View key={i} style={styles.reasonRow}>
              <Ionicons
                name={reason.includes('caution') || reason.includes('Negative') ? 'warning-outline' : 'checkmark-circle-outline'}
                size={15}
                color={reason.includes('caution') || reason.includes('Negative') ? Colors.warning : Colors.primary}
              />
              <Text style={styles.reasonText}>{reason}</Text>
            </View>
          ))}
        </SectionCard>
      )}

      {/* ── Open in TradingView ──────────────────────────────────────── */}
      <TouchableOpacity
        style={styles.tvButton}
        onPress={() => Linking.openURL(`https://www.tradingview.com/chart/?symbol=NSE%3A${symbol}`)}
      >
        <Ionicons name="bar-chart" size={18} color={Colors.primary} />
        <Text style={styles.tvButtonText}>Open NSE:{symbol} on TradingView</Text>
      </TouchableOpacity>
    </ScrollView>
  );
};

// ── Sub-components ─────────────────────────────────────────────────────────

const SectionCard: React.FC<{ title: string; children: React.ReactNode }> = ({
  title, children,
}) => (
  <View style={sectionStyles.card}>
    <Text style={sectionStyles.title}>{title}</Text>
    {children}
  </View>
);

const TradeBox: React.FC<{
  label: string; value: string; subtitle?: string; color: string;
}> = ({ label, value, subtitle, color }) => (
  <View style={[tradeStyles.box, { borderColor: color + '44', backgroundColor: color + '11' }]}>
    <Text style={tradeStyles.label}>{label}</Text>
    <Text style={[tradeStyles.value, { color }]}>{value}</Text>
    {subtitle ? <Text style={[tradeStyles.sub, { color }]}>{subtitle}</Text> : null}
  </View>
);

const IndBox: React.FC<{ label: string; value?: string; unit: string }> = ({
  label, value, unit,
}) => (
  <View style={indStyles.box}>
    <Text style={indStyles.label}>{label}</Text>
    <Text style={indStyles.value}>{value ?? '—'}{unit}</Text>
  </View>
);

// ── Styles ─────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  centered: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: Spacing.xl },
  loadingText: { color: Colors.textSecondary, marginTop: Spacing.md },
  errorText: { color: Colors.loss, marginTop: Spacing.sm, fontSize: 16, fontWeight: '700' },
  retryText: { color: Colors.primary, marginTop: Spacing.md, fontSize: 14, fontWeight: '600' },
  hero: {
    flexDirection: 'row', alignItems: 'center',
    padding: Spacing.lg, backgroundColor: Colors.surface,
    borderBottomWidth: 1, borderColor: Colors.border,
  },
  heroSymbol: { color: Colors.textPrimary, fontSize: 28, fontWeight: '800', letterSpacing: 0.5 },
  heroName: { color: Colors.textSecondary, fontSize: 13, marginTop: 2 },
  sectorPill: {
    marginTop: 6, alignSelf: 'flex-start',
    backgroundColor: Colors.accent + '20', borderRadius: Radius.full,
    paddingHorizontal: 10, paddingVertical: 3,
  },
  sectorText: { color: Colors.accent, fontSize: 10, fontWeight: '700' },
  scoreCircle: {
    width: 68, height: 68, borderRadius: 34, borderWidth: 3,
    alignItems: 'center', justifyContent: 'center',
  },
  scoreNum: { fontSize: 22, fontWeight: '900' },
  scoreLabel: { fontSize: 9, fontWeight: '700', marginTop: -2 },
  tradeGrid: { flexDirection: 'row', gap: Spacing.sm },
  noteBox: {
    flexDirection: 'row', gap: 6, marginTop: Spacing.md,
    backgroundColor: Colors.warning + '11', borderRadius: Radius.sm,
    padding: Spacing.sm, alignItems: 'flex-start',
  },
  noteText: { color: Colors.warning, fontSize: 11, flex: 1, lineHeight: 16 },
  indicatorGrid: {
    flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.sm,
  },
  patternContainer: { marginTop: Spacing.md },
  patternTitle: { color: Colors.textSecondary, fontSize: 11, fontWeight: '700', marginBottom: 6 },
  patternRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  patternPill: {
    backgroundColor: Colors.primary + '22', borderRadius: Radius.full,
    paddingHorizontal: 10, paddingVertical: 4, borderWidth: 1, borderColor: Colors.primary + '44',
  },
  patternText: { color: Colors.primary, fontSize: 10, fontWeight: '700', letterSpacing: 0.5 },
  reasonRow: {
    flexDirection: 'row', gap: 8, marginBottom: 8, alignItems: 'flex-start',
  },
  reasonText: { color: Colors.textSecondary, fontSize: 13, flex: 1, lineHeight: 18 },
  tvButton: {
    margin: Spacing.md, flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: 8, backgroundColor: Colors.primary + '15',
    borderRadius: Radius.md, padding: Spacing.md,
    borderWidth: 1, borderColor: Colors.primary + '44',
  },
  tvButtonText: { color: Colors.primary, fontWeight: '700', fontSize: 14 },
});

const sectionStyles = StyleSheet.create({
  card: {
    margin: Spacing.md, marginBottom: 0,
    backgroundColor: Colors.card, borderRadius: Radius.md,
    padding: Spacing.md, borderWidth: 1, borderColor: Colors.border,
    ...Shadow.card,
  },
  title: {
    color: Colors.textPrimary, fontSize: 14, fontWeight: '800',
    marginBottom: Spacing.md, textTransform: 'uppercase', letterSpacing: 0.8,
  },
});

const tradeStyles = StyleSheet.create({
  box: {
    flex: 1, borderRadius: Radius.sm, borderWidth: 1,
    padding: Spacing.sm, alignItems: 'center',
  },
  label: { color: Colors.textMuted, fontSize: 10, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.3 },
  value: { fontSize: 18, fontWeight: '800', marginTop: 4 },
  sub: { fontSize: 11, fontWeight: '700', marginTop: 2 },
});

const indStyles = StyleSheet.create({
  box: {
    width: '47%', backgroundColor: Colors.surface, borderRadius: Radius.sm,
    padding: Spacing.sm,
  },
  label: { color: Colors.textMuted, fontSize: 10, fontWeight: '600', textTransform: 'uppercase' },
  value: { color: Colors.textPrimary, fontSize: 14, fontWeight: '700', marginTop: 3 },
});
