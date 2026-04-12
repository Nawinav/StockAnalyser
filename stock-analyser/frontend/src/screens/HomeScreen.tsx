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
    staleTime: 5 * 60 * 1000,       // 5 min
    retry: 2,
  });

  const { data: marketStatus } = useQuery({
    queryKey: ['market-status'],
    queryFn: getMarketStatus,
    refetchInterval: 60 * 1000,     // refresh every minute
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
      const hasTopPicks = (latest?.recommendations?.length ?? 0) >= MAX_PICKS;

      if (isFreshRun && hasTopPicks) {
        qc.invalidateQueries({ queryKey: ['today'] });
        qc.invalidateQueries({ queryKey: ['market-status'] });
        Alert.alert('Analysis Complete', 'Today\'s Picks have been updated with the latest live market data.');
        return;
      }

      await wait(pollEveryMs);
    }

    Alert.alert('Still Processing', 'Analysis is taking longer than expected. Pull to refresh in a minute.');
  };

  const handleTriggerAnalysis = async () => {
    Alert.alert(
      'Run Analysis Now',
      'This will scan all NSE stocks and generate fresh recommendations. It takes ~5 minutes.',
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
              Alert.alert('Analysis Started', 'Fetching live market data and recalculating scores...');
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

  const updatedStr = dataUpdatedAt
    ? new Date(dataUpdatedAt).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })
    : null;

  // ── Render ──────────────────────────────────────────────────────────────

  return (
    <View style={styles.container}>
      <MarketStatusBar status={marketStatus} />

      {isLoading && (
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={Colors.primary} />
          <Text style={styles.loadingText}>Loading recommendations…</Text>
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
          data={todayData?.recommendations ?? []}
          keyExtractor={(item) => String(item.id)}
          renderItem={({ item }) => <StockCard rec={item} onPress={handleStockPress} />}
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
          ListHeaderComponent={
            <View style={styles.listHeader}>
              <View>
                <Text style={styles.dateText}>
                  {todayData?.trade_date
                    ? new Date(todayData.trade_date).toLocaleDateString('en-IN', {
                        weekday: 'long', day: 'numeric', month: 'long',
                      })
                    : new Date().toLocaleDateString('en-IN', {
                        weekday: 'long', day: 'numeric', month: 'long',
                      })}
                </Text>
                {updatedStr && (
                  <Text style={styles.updatedText}>Last updated: {updatedStr}</Text>
                )}
              </View>
              <TouchableOpacity
                style={styles.refreshBtn}
                onPress={handleTriggerAnalysis}
                disabled={triggering}
              >
                {triggering
                  ? <ActivityIndicator size="small" color={Colors.primary} />
                  : <Ionicons name="refresh" size={20} color={Colors.primary} />}
              </TouchableOpacity>
            </View>
          }
          ListEmptyComponent={
            <View style={styles.emptyContainer}>
              <Ionicons name="bar-chart-outline" size={64} color={Colors.textMuted} />
              <Text style={styles.emptyTitle}>No recommendations yet</Text>
              <Text style={styles.emptySub}>
                Analysis runs automatically at 8:30 AM IST.{'\n'}
                Tap the refresh button to run it manually now.
              </Text>
              <TouchableOpacity
                style={styles.analyseBtn}
                onPress={handleTriggerAnalysis}
                disabled={triggering}
              >
                {triggering
                  ? <ActivityIndicator size="small" color="#fff" />
                  : <Text style={styles.analyseBtnText}>Run Analysis Now</Text>}
              </TouchableOpacity>
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
  list: { paddingVertical: Spacing.sm, paddingBottom: 80 },
  listHeader: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingHorizontal: Spacing.md, paddingTop: Spacing.md, paddingBottom: Spacing.sm,
  },
  dateText: { color: Colors.textPrimary, fontSize: 16, fontWeight: '700' },
  updatedText: { color: Colors.textMuted, fontSize: 11, marginTop: 2 },
  refreshBtn: {
    width: 40, height: 40, borderRadius: 20,
    backgroundColor: Colors.primary + '22',
    alignItems: 'center', justifyContent: 'center',
    borderWidth: 1, borderColor: Colors.primary + '44',
  },
  emptyContainer: {
    alignItems: 'center', justifyContent: 'center',
    padding: Spacing.xl, marginTop: Spacing.xl,
  },
  emptyTitle: {
    color: Colors.textPrimary, fontSize: 20, fontWeight: '700', marginTop: Spacing.lg,
  },
  emptySub: {
    color: Colors.textSecondary, fontSize: 13, textAlign: 'center',
    marginTop: Spacing.sm, lineHeight: 20,
  },
  analyseBtn: {
    marginTop: Spacing.xl, backgroundColor: Colors.primary,
    paddingHorizontal: Spacing.xl, paddingVertical: 14,
    borderRadius: Radius.full,
  },
  analyseBtnText: { color: '#000', fontWeight: '800', fontSize: 15 },
});
