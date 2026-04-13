import React, { useState } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity, ActivityIndicator,
  Linking, Platform,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { LongTermStock, NewsItem } from '../types';
import { Colors, Spacing, Radius, Shadow } from '../theme';
import { getStockNews } from '../services/api';

interface Props {
  stock: LongTermStock;
  isWatchlisted: boolean;
  onWatchlistToggle: (stock: LongTermStock) => void;
  onPress: (symbol: string) => void;
}

const fmt = (n?: number | null, dec = 2): string =>
  n !== undefined && n !== null ? n.toFixed(dec) : '—';

function holdColor(period?: string): string {
  if (!period) return Colors.textSecondary;
  if (period.includes('year') || period.includes('2')) return Colors.profit;
  if (period.includes('12') || period.includes('6')) return Colors.warning;
  return Colors.info;
}

function scoreColor(score?: number): string {
  if (!score) return Colors.neutral;
  if (score >= 75) return Colors.scoreHigh;
  if (score >= 55) return Colors.scoreMid;
  return Colors.scoreLow;
}

export const LongTermCard: React.FC<Props> = ({
  stock, isWatchlisted, onWatchlistToggle, onPress,
}) => {
  const [showNews, setShowNews] = useState(false);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [loadingNews, setLoadingNews] = useState(false);

  const sc = scoreColor(stock.total_score);
  const hc = holdColor(stock.hold_period);

  const handleNewsToggle = async () => {
    if (!showNews && news.length === 0) {
      setLoadingNews(true);
      try {
        const fetched = await getStockNews(stock.symbol);
        setNews(fetched);
      } catch {
        setNews([]);
      } finally {
        setLoadingNews(false);
      }
    }
    setShowNews((v) => !v);
  };

  return (
    <View style={styles.card}>
      {/* ── Header ── */}
      <TouchableOpacity style={styles.header} activeOpacity={0.82} onPress={() => onPress(stock.symbol)}>
        <View style={styles.rankBadge}>
          <Text style={styles.rankText}>#{stock.rank}</Text>
        </View>
        <View style={{ flex: 1, marginLeft: Spacing.sm }}>
          <Text style={styles.symbol}>{stock.symbol}</Text>
          {stock.company_name ? (
            <Text style={styles.companyName} numberOfLines={1}>{stock.company_name}</Text>
          ) : null}
          {stock.sector ? (
            <View style={styles.sectorPill}>
              <Text style={styles.sectorText}>{stock.sector}</Text>
            </View>
          ) : null}
        </View>
        {/* Score */}
        <View style={[styles.scoreBadge, { borderColor: sc }]}>
          <Text style={[styles.scoreText, { color: sc }]}>{stock.total_score ?? '—'}</Text>
          <Text style={[styles.scoreLabel, { color: sc }]}>score</Text>
        </View>
        {/* Watchlist button */}
        <TouchableOpacity
          onPress={() => onWatchlistToggle(stock)}
          style={styles.watchlistBtn}
          hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
        >
          <Ionicons
            name={isWatchlisted ? 'bookmark' : 'bookmark-outline'}
            size={22}
            color={isWatchlisted ? Colors.warning : Colors.textSecondary}
          />
        </TouchableOpacity>
      </TouchableOpacity>

      {/* ── Hold period banner ── */}
      <View style={[styles.holdBanner, { borderLeftColor: hc }]}>
        <Ionicons name="time-outline" size={13} color={hc} style={{ marginRight: 4 }} />
        <Text style={[styles.holdPeriod, { color: hc }]}>Hold: {stock.hold_period ?? '—'}</Text>
        {stock.hold_rationale ? (
          <Text style={styles.holdRationale} numberOfLines={2}> · {stock.hold_rationale}</Text>
        ) : null}
      </View>

      {/* ── Fundamental grid ── */}
      <View style={styles.fundGrid}>
        <FundBox label="P/E"     value={fmt(stock.pe_ratio, 1)} />
        <FundBox label="ROE"     value={stock.roe != null ? `${fmt(stock.roe, 1)}%` : '—'} />
        <FundBox label="D/E"     value={fmt(stock.debt_to_equity, 1)} />
        <FundBox label="Rev Gr"  value={stock.revenue_growth != null ? `${fmt(stock.revenue_growth, 1)}%` : '—'} />
        <FundBox label="EPS"     value={fmt(stock.eps_ttm, 2)} />
        <FundBox label="Div"     value={stock.dividend_yield != null ? `${fmt(stock.dividend_yield, 1)}%` : '—'} />
      </View>

      {/* ── Price info ── */}
      <View style={styles.priceRow}>
        <Text style={styles.priceLabel}>CMP</Text>
        <Text style={styles.priceValue}>₹{fmt(stock.current_price)}</Text>
        {stock.week52_high && stock.week52_low ? (
          <Text style={styles.priceSub}>
            52W  ₹{fmt(stock.week52_low)} – ₹{fmt(stock.week52_high)}
          </Text>
        ) : null}
      </View>

      {/* ── Score breakdown ── */}
      <View style={styles.scoreRow}>
        <ScorePill label="Fundamental" value={stock.fundamental_score} color={Colors.primary} />
        <ScorePill label="Technical"   value={stock.technical_score}   color={Colors.accent} />
      </View>

      {/* ── News toggle ── */}
      <TouchableOpacity style={styles.newsToggle} onPress={handleNewsToggle} activeOpacity={0.8}>
        {loadingNews ? (
          <ActivityIndicator size="small" color={Colors.primary} />
        ) : (
          <Ionicons
            name={showNews ? 'chevron-up' : 'newspaper-outline'}
            size={15}
            color={Colors.primary}
          />
        )}
        <Text style={styles.newsToggleText}>
          {loadingNews ? 'Loading news…' : showNews ? 'Hide news' : 'Show news'}
        </Text>
      </TouchableOpacity>

      {/* ── News items ── */}
      {showNews && (
        <View style={styles.newsList}>
          {news.length === 0 ? (
            <Text style={styles.noNews}>No recent news available.</Text>
          ) : (
            news.map((item, i) => (
              <TouchableOpacity
                key={i}
                style={styles.newsItem}
                onPress={() => item.link && Linking.openURL(item.link)}
                activeOpacity={0.75}
              >
                <Text style={styles.newsTitle} numberOfLines={2}>{item.title}</Text>
                <View style={styles.newsMeta}>
                  <Text style={styles.newsPublisher}>{item.publisher}</Text>
                  {item.published_at ? (
                    <Text style={styles.newsDate}>
                      {new Date(item.published_at * 1000).toLocaleDateString('en-IN', {
                        day: 'numeric', month: 'short',
                      })}
                    </Text>
                  ) : null}
                </View>
              </TouchableOpacity>
            ))
          )}
        </View>
      )}
    </View>
  );
};

const FundBox: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <View style={styles.fundBox}>
    <Text style={styles.fundLabel}>{label}</Text>
    <Text style={styles.fundValue}>{value}</Text>
  </View>
);

const ScorePill: React.FC<{ label: string; value?: number; color: string }> = ({ label, value, color }) => (
  <View style={[styles.scorePill, { borderColor: color + '55' }]}>
    <Text style={[styles.scorePillValue, { color }]}>{value ?? '—'}</Text>
    <Text style={styles.scorePillLabel}>{label}</Text>
  </View>
);

const styles = StyleSheet.create({
  card: {
    backgroundColor: Colors.card,
    borderRadius: Radius.md,
    marginHorizontal: Spacing.md,
    marginBottom: Spacing.sm,
    overflow: 'hidden',
    ...Shadow.card,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: Spacing.md,
    paddingBottom: Spacing.sm,
  },
  rankBadge: {
    width: 32, height: 32,
    borderRadius: 16,
    backgroundColor: Colors.surface,
    alignItems: 'center', justifyContent: 'center',
  },
  rankText: { color: Colors.textSecondary, fontSize: 11, fontWeight: '700' },
  symbol: { color: Colors.textPrimary, fontSize: 16, fontWeight: '800', letterSpacing: 0.5 },
  companyName: { color: Colors.textSecondary, fontSize: 11, marginTop: 1 },
  sectorPill: {
    marginTop: 3,
    backgroundColor: Colors.border,
    borderRadius: Radius.sm,
    paddingHorizontal: 6, paddingVertical: 1,
    alignSelf: 'flex-start',
  },
  sectorText: { color: Colors.textMuted, fontSize: 10 },
  scoreBadge: {
    width: 50, height: 50,
    borderRadius: 25,
    borderWidth: 2,
    alignItems: 'center', justifyContent: 'center',
    marginRight: Spacing.xs,
  },
  scoreText: { fontSize: 16, fontWeight: '800' },
  scoreLabel: { fontSize: 8, fontWeight: '600', marginTop: -2 },
  watchlistBtn: { padding: Spacing.xs },

  holdBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.surface,
    borderLeftWidth: 3,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.xs,
  },
  holdPeriod: { fontSize: 12, fontWeight: '700' },
  holdRationale: { color: Colors.textMuted, fontSize: 11, flex: 1 },

  fundGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    paddingHorizontal: Spacing.sm,
    paddingTop: Spacing.sm,
  },
  fundBox: {
    width: '33.3%',
    paddingHorizontal: Spacing.xs,
    paddingVertical: Spacing.xs,
  },
  fundLabel: { color: Colors.textMuted, fontSize: 10 },
  fundValue: { color: Colors.textPrimary, fontSize: 13, fontWeight: '700', marginTop: 1 },

  priceRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    paddingHorizontal: Spacing.md,
    paddingTop: Spacing.xs,
    paddingBottom: Spacing.xs,
    gap: Spacing.xs,
  },
  priceLabel: { color: Colors.textMuted, fontSize: 11 },
  priceValue: { color: Colors.textPrimary, fontSize: 15, fontWeight: '800' },
  priceSub: { color: Colors.textSecondary, fontSize: 10, marginLeft: 'auto' as any },

  scoreRow: {
    flexDirection: 'row',
    paddingHorizontal: Spacing.md,
    paddingBottom: Spacing.sm,
    gap: Spacing.sm,
  },
  scorePill: {
    flexDirection: 'row', alignItems: 'center',
    borderWidth: 1, borderRadius: Radius.full,
    paddingHorizontal: Spacing.sm, paddingVertical: 3,
    gap: 4,
  },
  scorePillValue: { fontSize: 12, fontWeight: '800' },
  scorePillLabel: { color: Colors.textSecondary, fontSize: 11 },

  newsToggle: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
    gap: 6,
  },
  newsToggleText: { color: Colors.primary, fontSize: 12, fontWeight: '600' },
  newsList: { paddingHorizontal: Spacing.md, paddingBottom: Spacing.sm },
  noNews: { color: Colors.textMuted, fontSize: 12, textAlign: 'center', paddingVertical: Spacing.sm },
  newsItem: {
    paddingVertical: Spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  newsTitle: { color: Colors.textPrimary, fontSize: 12, lineHeight: 17 },
  newsMeta: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 3 },
  newsPublisher: { color: Colors.primary, fontSize: 10 },
  newsDate: { color: Colors.textMuted, fontSize: 10 },
});
