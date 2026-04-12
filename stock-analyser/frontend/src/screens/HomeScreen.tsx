import React, { useCallback, useState } from 'react';
import {
  View, Text, FlatList, StyleSheet, RefreshControl,
  TouchableOpacity, ActivityIndicator, Alert,
} from 'react-native';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Ionicons } from '@expo/vector-icons';

import { getTodayRecommendations, getMarketStatus, triggerAnalysis } from '../services/api';
import { StockCard } from '../components/StockCard';
import { MarketStatusBar } from '../components/MarketStatusBar';
import { Colors, Spacing, Radius } from '../theme';
import { Recommendation } from '../types';

interface Props {
  navigation: any;
}

export const HomeScreen: React.FC<Props> = ({ navigation }) => {
  const qc = useQueryClient();
  const [triggering, setTriggering] = useState(false);
  const MAX_PICKS = 10;

  const {
    data: todayData,
    isLoading,
    isError,
    refetch,
    dataUpdatedAt,
  } = useQuery({
    queryKey: ['today'],
    queryFn: getTodayRecommendations,
    staleTime: 5 * 60 * 1000,
    retry: 2,
  });

  const { data: marketStatus } = useQuery({
    queryKey: ['market-status'],
    queryFn: getMarketStatus,
    refetchInterval: 60 * 1000,
    staleTime: 30 * 1000,
  });

  const onRefresh = useCallback(() => {
    qc.invalidateQueries({ queryKey: ['today'] });
    qc.invalidateQueries({ queryKey: ['market-status'] });
  }, [qc]);

  const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

  const waitForFreshAnalysis = async (previousAnalyzedAt?: string) => {
    const timeoutMs = 7 * 60 * 1000;
    const pollEveryMs = 10 * 1000;
    const startedAt = Date.now();

    while (Date.now() - startedAt < timeoutMs) {
      const queryResult = await refetch();
      const latest = queryResult.data;
      const isFreshRun = !!latest?.analyzed_at && latest.analyzed_at !== previousAnalyzedAt;
      const hasTopPicks = (latest?.recommendations?.length ?? 0) > 0;

      if (isFreshRun && hasTopPicks) {
        qc.invalidateQueries({ queryKey: ['today'] });
        qc.invalidateQueries({ queryKey: ['market-status'] });
        Alert.alert(
          'Analysis Complete',
          `Today's Picks updated — top ${latest?.recommendations?.length ?? MAX_PICKS} stocks ranked by score.`,
        );
        return;
      }

      await wait(pollEveryMs);
    }

    Alert.alert('Still Processing', 'Analysis is taking longer than expected. Pull to refresh in a minute.');
  };

  const handleTriggerAnalysis = async () => {
    Alert.alert(
      'Run Analysis Now',
      'This will scan all NSE stocks, score each one and update Today\'s Picks with the top 10. Takes ~5 minutes.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Start',
          style: 'default',
          onPress: async () => {
            setTriggering(true);
            try {
              const previousAnalyzedAt = todayData?.analyzed_at;
              await triggerAnalysis();
              Alert.alert('Analysis Started', 'Scanning all NSE stocks and recalculating scores…');
              await waitForFreshAnalysis(previousAnalyzedAt);
            } catch {
              Alert.alert('Error', 'Could not connect to the backend. Make sure the server is running.');
            } finally {
              setTriggering(false);
            }
          },
        },
      ]
    );
  };

  const handleStockPress = (rec: Recommendation) => {
    navigation.navigate('StockDetail', { symbol: rec.symbol, rec });
  };

  // Top 10 sorted by score descending (backend already orders correctly; slice is a safety net)
  const topPicks: Recommendation[] = [...(todayData?.recommendations ?? [])]
    .sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
    .slice(0, MAX_PICKS);

  const analyzedStr = todayData?.analyzed_at
    ? new Date(todayData.analyzed_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })
    : null;

  const niftyTrend = todayData?.nifty_trend ?? marketStatus?.nifty_trend;
  const trendColor =
    niftyTrend === 'bullish' ? Colors.profit :
    niftyTrend === 'bearish' ? Colors.loss :
    Colors.textSecondary;
  const trendBg =
    niftyTrend === 'bullish' ? Colors.profit + '22' :
    niftyTrend === 'bearish' ? Colors.loss + '22' :
    Colors.border;

  // ── Shared header shown above both the list and empty state ─────────────
  const renderPicksHeader = () => (
    <View style={styles.picksHeader}>
      {/* Title row */}
      <View style={styles.titleRow}>
        <View>
          <Text style={styles.picksTitle}>Today's Picks</Text>
          <Text style={styles.picksSubtitle}>
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

      {/* Stats row */}
      {topPicks.length > 0 && (
        <View style={styles.statsRow}>
          <View style={styles.statChip}>
            <Ionicons name="trophy-outline" size={12} color={Colors.primary} />
            <Text style={styles.statChipText}>Top {topPicks.length} by score</Text>
          </View>
          {analyzedStr && (
            <Text style={styles.analyzedText}>Analysed at {analyzedStr}</Text>
          )}
        </View>
      )}

      {/* Run Analysis Button — always visible */}
      <TouchableOpacity
        style={[styles.runBtn, triggering && styles.runBtnActive]}
        onPress={handleTriggerAnalysis}
        disabled={triggering}
        activeOpacity={0.8}
      >
        {triggering ? (
          <>
            <ActivityIndicator size="small" color="#000" style={{ marginRight: 8 }} />
            <Text style={styles.runBtnText}>Analysing all stocks…</Text>
          </>
        ) : (
          <>
            <Ionicons name="refresh-circle" size={18} color="#000" style={{ marginRight: 6 }} />
            <Text style={styles.runBtnText}>Run Analysis Now</Text>
          </>
        )}
      </TouchableOpacity>
    </View>
  );

  // ── Render ───────────────────────────────────────────────────────────────

  return (
    <View style={styles.container}>
      <MarketStatusBar status={marketStatus} />

      {isLoading && (
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={Colors.primary} />
          <Text style={styles.loadingText}>Loading Today's Picks…</Text>
        </View>
      )}

      {isError && !isLoading && (
        <View style={styles.centered}>
          <Ionicons name="alert-circle-outline" size={52} color={Colors.loss} />
          <Text style={styles.errorTitle}>Cannot reach backend</Text>
          <Text style={styles.errorSub}>
            Make sure the Python server is running on port 8000
          </Text>
          <TouchableOpacity style={styles.retryBtn} onPress={() => refetch()}>
            <Text style={styles.retryText}>Retry</Text>
          </TouchableOpacity>
        </View>
      )}

      {!isLoading && !isError && (
        <FlatList
          data={topPicks}
          keyExtractor={(item) => String(item.id)}
          renderItem={({ item, index }) => (
            <StockCard rec={{ ...item, rank: index + 1 }} onPress={handleStockPress} />
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
          ListHeaderComponent={renderPicksHeader()}
          ListEmptyComponent={
            <View style={styles.emptyContainer}>
              <Ionicons name="bar-chart-outline" size={64} color={Colors.textMuted} />
              <Text style={styles.emptyTitle}>No picks yet for today</Text>
              <Text style={styles.emptySub}>
                The scheduler runs automatically at 8:30 AM IST.{'\n'}
                Tap "Run Analysis Now" above to generate picks immediately.
              </Text>
            </View>
          }
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
    marginTop: Spacing.lg, backgroundColor: Colors.primary, paddingHorizontal: 24,
    paddingVertical: 10, borderRadius: Radius.full,
  },
  retryText: { color: '#000', fontWeight: '700', fontSize: 14 },
  list: { paddingBottom: 80 },

  // ── Picks header ─────────────────────────────────────────────────────
  picksHeader: {
    paddingHorizontal: Spacing.md,
    paddingTop: Spacing.md,
    paddingBottom: Spacing.sm,
    gap: Spacing.sm,
  },
  titleRow: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
  },
  picksTitle: {
    color: Colors.textPrimary, fontSize: 22, fontWeight: '800', letterSpacing: 0.3,
  },
  picksSubtitle: {
    color: Colors.textSecondary, fontSize: 12, marginTop: 2,
  },
  trendPill: {
    paddingHorizontal: 10, paddingVertical: 4, borderRadius: Radius.full,
  },
  trendText: { fontSize: 11, fontWeight: '700', letterSpacing: 0.5 },

  statsRow: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
  },
  statChip: {
    flexDirection: 'row', alignItems: 'center', gap: 4,
    backgroundColor: Colors.primary + '18',
    paddingHorizontal: 10, paddingVertical: 4, borderRadius: Radius.full,
    borderWidth: 1, borderColor: Colors.primary + '33',
  },
  statChipText: { color: Colors.primary, fontSize: 12, fontWeight: '600' },
  analyzedText: { color: Colors.textMuted, fontSize: 11 },

  runBtn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    backgroundColor: Colors.primary,
    paddingVertical: 13, borderRadius: Radius.full,
    marginTop: Spacing.xs,
  },
  runBtnActive: { opacity: 0.75 },
  runBtnText: { color: '#000', fontWeight: '800', fontSize: 14 },

  // ── Empty state ───────────────────────────────────────────────────────
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
});
