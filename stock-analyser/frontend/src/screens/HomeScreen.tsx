import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  View, Text, FlatList, StyleSheet, RefreshControl,
  TouchableOpacity, ActivityIndicator, Alert,
} from 'react-native';
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query';
import { Ionicons } from '@expo/vector-icons';

import {
  getIntradayTop10, getLongTermTop10, getMarketStatus,
  addToWatchlist, removeFromWatchlist, getWatchlist,
} from '../services/api';
import { StockCard }     from '../components/StockCard';
import { LongTermCard }  from '../components/LongTermCard';
import { MarketStatusBar } from '../components/MarketStatusBar';
import { Colors, Spacing, Radius } from '../theme';
import { IntradayStock, LongTermStock } from '../types';

interface Props {
  navigation: any;
}

const INTRADAY_REFRESH_MS = 10 * 60 * 1000;
const REFRESH_COUNTDOWN_S = 10 * 60;

type Section = 'intraday' | 'longterm';

export const HomeScreen: React.FC<Props> = ({ navigation }) => {
  const qc = useQueryClient();
  const [activeSection, setActiveSection] = useState<Section>('intraday');
  const [countdown, setCountdown] = useState(REFRESH_COUNTDOWN_S);
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Market status ─────────────────────────────────────────────────────────
  const { data: marketStatus } = useQuery({
    queryKey: ['market-status'],
    queryFn: getMarketStatus,
    refetchInterval: 60 * 1000,
    staleTime: 30 * 1000,
  });

  // ── Intraday data — auto-refresh every 10 min ─────────────────────────────
  const {
    data: intradayData,
    isLoading: intradayLoading,
    isError: intradayError,
    refetch: refetchIntraday,
    dataUpdatedAt: intradayUpdatedAt,
  } = useQuery({
    queryKey: ['intraday'],
    queryFn: getIntradayTop10,
    staleTime: INTRADAY_REFRESH_MS,
    refetchInterval: INTRADAY_REFRESH_MS,
    retry: 2,
  });

  // ── Long-term data — refresh hourly ───────────────────────────────────────
  const {
    data: longTermData,
    isLoading: longTermLoading,
    isError: longTermError,
    refetch: refetchLongTerm,
  } = useQuery({
    queryKey: ['longterm'],
    queryFn: getLongTermTop10,
    staleTime: 60 * 60 * 1000,
    refetchInterval: 60 * 60 * 1000,
    retry: 2,
  });

  // ── Watchlist ─────────────────────────────────────────────────────────────
  const { data: watchlistData } = useQuery({
    queryKey: ['watchlist'],
    queryFn: () => getWatchlist(false),
    staleTime: 5 * 60 * 1000,
  });

  const watchlistSymbols = new Set((watchlistData ?? []).map((w) => w.symbol));

  const addMutation = useMutation({
    mutationFn: addToWatchlist,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['watchlist'] }),
    onError:   () => Alert.alert('Error', 'Could not add to watchlist.'),
  });

  const removeMutation = useMutation({
    mutationFn: removeFromWatchlist,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['watchlist'] }),
    onError:   () => Alert.alert('Error', 'Could not remove from watchlist.'),
  });

  const handleWatchlistToggle = (stock: LongTermStock) => {
    if (watchlistSymbols.has(stock.symbol)) {
      Alert.alert(
        'Remove from Watchlist',
        `Remove ${stock.symbol} from your watchlist?`,
        [
          { text: 'Cancel', style: 'cancel' },
          {
            text: 'Remove',
            style: 'destructive',
            onPress: () => removeMutation.mutate(stock.symbol),
          },
        ],
      );
    } else {
      addMutation.mutate({
        symbol:       stock.symbol,
        company_name: stock.company_name,
        sector:       stock.sector,
        added_price:  stock.current_price,
        score:        stock.total_score,
        hold_period:  stock.hold_period,
      });
    }
  };

  // ── Countdown timer ───────────────────────────────────────────────────────
  useEffect(() => {
    setCountdown(REFRESH_COUNTDOWN_S);
  }, [intradayUpdatedAt]);

  useEffect(() => {
    countdownRef.current = setInterval(() => {
      setCountdown((c) => (c > 0 ? c - 1 : 0));
    }, 1000);
    return () => {
      if (countdownRef.current) clearInterval(countdownRef.current);
    };
  }, []);

  // ── Pull-to-refresh ───────────────────────────────────────────────────────
  const onRefresh = useCallback(() => {
    if (activeSection === 'intraday') {
      qc.invalidateQueries({ queryKey: ['intraday'] });
    } else {
      qc.invalidateQueries({ queryKey: ['longterm'] });
    }
    qc.invalidateQueries({ queryKey: ['market-status'] });
  }, [qc, activeSection]);

  const handleIntradayPress = (stock: IntradayStock) => {
    navigation.navigate('StockDetail', { symbol: stock.symbol, rec: stock as any });
  };

  const handleLongTermPress = (symbol: string) => {
    navigation.navigate('StockDetail', { symbol });
  };

  const fmtCountdown = (secs: number) => {
    const m = Math.floor(secs / 60).toString().padStart(2, '0');
    const s = (secs % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  const niftyTrend = intradayData?.nifty_trend ?? marketStatus?.nifty_trend;
  const trendColor =
    niftyTrend === 'bullish' ? Colors.profit :
    niftyTrend === 'bearish' ? Colors.loss :
    Colors.textSecondary;
  const trendBg =
    niftyTrend === 'bullish' ? Colors.profit + '22' :
    niftyTrend === 'bearish' ? Colors.loss + '22' :
    Colors.border;

  const snapshotDate = intradayData?.snapshot_at ? new Date(intradayData.snapshot_at) : null;
  const snapshotIsToday = snapshotDate
    ? snapshotDate.toDateString() === new Date().toDateString()
    : false;
  const snapshotStr = snapshotDate
    ? (snapshotIsToday
        ? `Today at ${snapshotDate.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}`
        : snapshotDate.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' }) +
          ` at ${snapshotDate.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}`)
    : null;

  const isMarketOpen = marketStatus?.is_open ?? false;

  // ── Section tabs ──────────────────────────────────────────────────────────
  const renderTabs = () => (
    <View style={styles.tabBar}>
      <TouchableOpacity
        style={[styles.tab, activeSection === 'intraday' && styles.tabActive]}
        onPress={() => setActiveSection('intraday')}
        activeOpacity={0.8}
      >
        <Ionicons
          name="flash"
          size={14}
          color={activeSection === 'intraday' ? Colors.primary : Colors.textMuted}
          style={{ marginRight: 4 }}
        />
        <Text style={[styles.tabText, activeSection === 'intraday' && styles.tabTextActive]}>
          Intraday
        </Text>
      </TouchableOpacity>
      <TouchableOpacity
        style={[styles.tab, activeSection === 'longterm' && styles.tabActive]}
        onPress={() => setActiveSection('longterm')}
        activeOpacity={0.8}
      >
        <Ionicons
          name="trending-up"
          size={14}
          color={activeSection === 'longterm' ? Colors.primary : Colors.textMuted}
          style={{ marginRight: 4 }}
        />
        <Text style={[styles.tabText, activeSection === 'longterm' && styles.tabTextActive]}>
          Long Term
        </Text>
      </TouchableOpacity>
    </View>
  );

  // ── Intraday header ───────────────────────────────────────────────────────
  const renderIntradayHeader = () => (
    <View style={styles.sectionHeader}>
      <View style={styles.sectionTitleRow}>
        <View>
          <Text style={styles.sectionTitle}>Intraday Picks</Text>
          <Text style={styles.sectionSubtitle}>
            {new Date().toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long' })}
          </Text>
        </View>
        {niftyTrend && (
          <View style={[styles.trendPill, { backgroundColor: trendBg }]}>
            <Text style={[styles.trendText, { color: trendColor }]}>
              NIFTY {niftyTrend.toUpperCase()}
            </Text>
          </View>
        )}
      </View>
      <View style={styles.refreshRow}>
        {isMarketOpen ? (
          <>
            <View style={styles.liveChip}>
              <View style={styles.liveDot} />
              <Text style={styles.liveText}>Live · Refreshing every 10 min</Text>
            </View>
            <View style={styles.countdownChip}>
              <Ionicons name="timer-outline" size={12} color={Colors.accent} />
              <Text style={styles.countdownText}>Next: {fmtCountdown(countdown)}</Text>
            </View>
          </>
        ) : (
          <View style={styles.marketClosedChip}>
            <Ionicons name="moon-outline" size={13} color={Colors.textMuted} />
            <Text style={styles.marketClosedText}>
              Market closed · {marketStatus?.status ?? 'After hours'}
            </Text>
          </View>
        )}
      </View>
      {snapshotStr && (
        <Text style={styles.snapshotText}>Last snapshot: {snapshotStr}</Text>
      )}
    </View>
  );

  // ── Long-term header ──────────────────────────────────────────────────────
  const renderLongTermHeader = () => (
    <View style={styles.sectionHeader}>
      <View style={styles.sectionTitleRow}>
        <View>
          <Text style={styles.sectionTitle}>Long-Term Picks</Text>
          <Text style={styles.sectionSubtitle}>
            Fundamental-heavy · Updated daily
            {longTermData?.run_date
              ? ` · ${new Date(longTermData.run_date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}`
              : ''}
          </Text>
        </View>
        <View style={styles.infoChip}>
          <Ionicons name="information-circle-outline" size={14} color={Colors.info} />
          <Text style={styles.infoChipText}>Tap bookmark to watchlist</Text>
        </View>
      </View>
      <View style={styles.legendRow}>
        <View style={styles.legendItem}>
          <View style={[styles.legendDot, { backgroundColor: Colors.scoreHigh }]} />
          <Text style={styles.legendText}>Score ≥75</Text>
        </View>
        <View style={styles.legendItem}>
          <View style={[styles.legendDot, { backgroundColor: Colors.scoreMid }]} />
          <Text style={styles.legendText}>50–74</Text>
        </View>
        <View style={styles.legendItem}>
          <View style={[styles.legendDot, { backgroundColor: Colors.scoreLow }]} />
          <Text style={styles.legendText}>{'<'}50</Text>
        </View>
      </View>
    </View>
  );

  // ── Empty states ──────────────────────────────────────────────────────────
  const renderIntradayEmpty = () => (
    <View style={styles.emptyContainer}>
      <Ionicons
        name={isMarketOpen ? 'flash-outline' : 'moon-outline'}
        size={56}
        color={Colors.textMuted}
      />
      <Text style={styles.emptyTitle}>
        {isMarketOpen ? 'No intraday picks yet' : 'Market is closed'}
      </Text>
      <Text style={styles.emptySub}>
        {isMarketOpen
          ? 'Picks refresh every 10 minutes during market hours (09:15 – 15:30 IST).'
          : `Market opens at 09:15 IST on weekdays.\nLast session data is shown once available.`}
      </Text>
      {isMarketOpen && (
        <TouchableOpacity style={styles.refreshBtn} onPress={() => refetchIntraday()}>
          <Text style={styles.refreshBtnText}>Refresh Now</Text>
        </TouchableOpacity>
      )}
    </View>
  );

  const renderLongTermEmpty = () => (
    <View style={styles.emptyContainer}>
      <Ionicons name="trending-up-outline" size={56} color={Colors.textMuted} />
      <Text style={styles.emptyTitle}>No long-term picks yet</Text>
      <Text style={styles.emptySub}>
        Fundamental analysis runs every morning at 08:00 IST.{'\n'}
        Pull down to refresh.
      </Text>
      <TouchableOpacity style={styles.refreshBtn} onPress={() => refetchLongTerm()}>
        <Text style={styles.refreshBtnText}>Refresh Now</Text>
      </TouchableOpacity>
    </View>
  );

  // ── Render ────────────────────────────────────────────────────────────────
  const isLoading = activeSection === 'intraday' ? intradayLoading : longTermLoading;
  const isError   = activeSection === 'intraday' ? intradayError   : longTermError;
  const intradayStocks = intradayData?.stocks ?? [];
  const longTermStocks = longTermData?.stocks ?? [];

  return (
    <View style={styles.container}>
      <MarketStatusBar status={marketStatus} />
      {renderTabs()}

      {isLoading && (
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={Colors.primary} />
          <Text style={styles.loadingText}>
            {activeSection === 'intraday' ? 'Loading intraday picks…' : 'Running fundamental analysis…'}
          </Text>
        </View>
      )}

      {isError && !isLoading && (
        <View style={styles.centered}>
          <Ionicons name="alert-circle-outline" size={52} color={Colors.loss} />
          <Text style={styles.errorTitle}>Cannot reach backend</Text>
          <Text style={styles.errorSub}>
            Make sure the Python server is running on port 8000
          </Text>
          <TouchableOpacity
            style={styles.retryBtn}
            onPress={() => activeSection === 'intraday' ? refetchIntraday() : refetchLongTerm()}
          >
            <Text style={styles.retryText}>Retry</Text>
          </TouchableOpacity>
        </View>
      )}

      {!isLoading && !isError && activeSection === 'intraday' && (
        <FlatList
          data={intradayStocks}
          keyExtractor={(item) => String(item.id)}
          renderItem={({ item, index }) => (
            <StockCard
              rec={{ ...item, rank: index + 1, trade_date: item.snapshot_at ?? '' } as any}
              onPress={() => handleIntradayPress(item)}
            />
          )}
          contentContainerStyle={styles.list}
          showsVerticalScrollIndicator={false}
          refreshControl={
            <RefreshControl
              refreshing={false}
              onRefresh={onRefresh}
              tintColor={Colors.primary}
              colors={[Colors.primary]}
            />
          }
          ListHeaderComponent={renderIntradayHeader()}
          ListEmptyComponent={renderIntradayEmpty()}
        />
      )}

      {!isLoading && !isError && activeSection === 'longterm' && (
        <FlatList
          data={longTermStocks}
          keyExtractor={(item) => String(item.id)}
          renderItem={({ item }) => (
            <LongTermCard
              stock={item}
              isWatchlisted={watchlistSymbols.has(item.symbol)}
              onWatchlistToggle={handleWatchlistToggle}
              onPress={handleLongTermPress}
            />
          )}
          contentContainerStyle={styles.list}
          showsVerticalScrollIndicator={false}
          refreshControl={
            <RefreshControl
              refreshing={false}
              onRefresh={onRefresh}
              tintColor={Colors.primary}
              colors={[Colors.primary]}
            />
          }
          ListHeaderComponent={renderLongTermHeader()}
          ListEmptyComponent={renderLongTermEmpty()}
        />
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  centered: {
    flex: 1, alignItems: 'center', justifyContent: 'center', padding: Spacing.xl,
  },
  loadingText: { color: Colors.textSecondary, marginTop: Spacing.md, fontSize: 14 },
  errorTitle: {
    color: Colors.textPrimary, fontSize: 18, fontWeight: '700', marginTop: Spacing.md,
  },
  errorSub: {
    color: Colors.textSecondary, fontSize: 13, textAlign: 'center', marginTop: Spacing.sm,
  },
  retryBtn: {
    marginTop: Spacing.lg, backgroundColor: Colors.primary,
    paddingHorizontal: 24, paddingVertical: 10, borderRadius: Radius.full,
  },
  retryText: { color: '#000', fontWeight: '700', fontSize: 14 },
  list: { paddingBottom: 90 },

  // ── Tab bar ─────────────────────────────────────────────────────────────
  tabBar: {
    flexDirection: 'row',
    backgroundColor: Colors.surface,
    marginHorizontal: Spacing.md,
    marginTop: Spacing.sm,
    borderRadius: Radius.lg,
    padding: 3,
  },
  tab: {
    flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    paddingVertical: 10, borderRadius: Radius.md,
  },
  tabActive: { backgroundColor: Colors.card },
  tabText: { color: Colors.textMuted, fontSize: 13, fontWeight: '600' },
  tabTextActive: { color: Colors.primary },

  // ── Section header ────────────────────────────────────────────────────────
  sectionHeader: {
    paddingHorizontal: Spacing.md,
    paddingTop: Spacing.md,
    paddingBottom: Spacing.sm,
    gap: Spacing.sm,
  },
  sectionTitleRow: {
    flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between',
  },
  sectionTitle: {
    color: Colors.textPrimary, fontSize: 20, fontWeight: '800', letterSpacing: 0.3,
  },
  sectionSubtitle: { color: Colors.textSecondary, fontSize: 12, marginTop: 2 },
  trendPill: {
    paddingHorizontal: 10, paddingVertical: 4, borderRadius: Radius.full, marginTop: 2,
  },
  trendText: { fontSize: 11, fontWeight: '700', letterSpacing: 0.5 },

  // Intraday live indicator
  refreshRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm },
  liveChip: {
    flexDirection: 'row', alignItems: 'center', gap: 5,
    backgroundColor: Colors.profit + '18',
    borderRadius: Radius.full, paddingHorizontal: 10, paddingVertical: 4,
    borderWidth: 1, borderColor: Colors.profit + '44',
  },
  liveDot: { width: 6, height: 6, borderRadius: 3, backgroundColor: Colors.profit },
  liveText: { color: Colors.profit, fontSize: 11, fontWeight: '600' },
  countdownChip: {
    flexDirection: 'row', alignItems: 'center', gap: 4,
    backgroundColor: Colors.accent + '18',
    borderRadius: Radius.full, paddingHorizontal: 10, paddingVertical: 4,
    borderWidth: 1, borderColor: Colors.accent + '44',
  },
  countdownText: { color: Colors.accent, fontSize: 11, fontWeight: '700' },
  snapshotText: { color: Colors.textMuted, fontSize: 11 },
  marketClosedChip: {
    flexDirection: 'row', alignItems: 'center', gap: 5,
    backgroundColor: Colors.border,
    borderRadius: Radius.full, paddingHorizontal: 10, paddingVertical: 4,
  },
  marketClosedText: { color: Colors.textMuted, fontSize: 11, fontWeight: '600' },

  // Long-term header
  infoChip: {
    flexDirection: 'row', alignItems: 'center', gap: 4,
    backgroundColor: Colors.info + '18',
    borderRadius: Radius.full, paddingHorizontal: 8, paddingVertical: 4,
  },
  infoChipText: { color: Colors.info, fontSize: 10, fontWeight: '600' },
  legendRow: { flexDirection: 'row', gap: Spacing.md },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  legendDot: { width: 8, height: 8, borderRadius: 4 },
  legendText: { color: Colors.textSecondary, fontSize: 11 },

  // Empty states
  emptyContainer: {
    alignItems: 'center', justifyContent: 'center',
    padding: Spacing.xl, marginTop: Spacing.lg,
  },
  emptyTitle: {
    color: Colors.textPrimary, fontSize: 18, fontWeight: '700', marginTop: Spacing.lg,
  },
  emptySub: {
    color: Colors.textSecondary, fontSize: 13, textAlign: 'center',
    marginTop: Spacing.sm, lineHeight: 20,
  },
  refreshBtn: {
    marginTop: Spacing.lg, backgroundColor: Colors.primary,
    paddingHorizontal: 24, paddingVertical: 10, borderRadius: Radius.full,
  },
  refreshBtnText: { color: '#000', fontWeight: '700', fontSize: 14 },
});

