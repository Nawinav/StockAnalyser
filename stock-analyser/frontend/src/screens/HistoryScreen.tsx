import React, { useCallback, useState } from 'react';
import {
  View, Text, FlatList, StyleSheet,
  RefreshControl, TouchableOpacity, SectionList,
} from 'react-native';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Ionicons } from '@expo/vector-icons';
import { getHistoryRecommendations } from '../services/api';
import { StockCard } from '../components/StockCard';
import { Colors, Spacing, Radius } from '../theme';
import { Recommendation } from '../types';

interface Props { navigation: any }

type DayFilter = 7 | 14 | 30;

export const HistoryScreen: React.FC<Props> = ({ navigation }) => {
  const qc = useQueryClient();
  const [days, setDays] = useState<DayFilter>(7);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['history', days],
    queryFn: () => getHistoryRecommendations(days),
    staleTime: 10 * 60 * 1000,
  });

  const onRefresh = useCallback(() => {
    qc.invalidateQueries({ queryKey: ['history'] });
  }, [qc]);

  // Group by trade_date
  const byDate: Record<string, Recommendation[]> = {};
  (data ?? []).forEach((r) => {
    if (!byDate[r.trade_date]) byDate[r.trade_date] = [];
    byDate[r.trade_date].push(r);
  });

  const sections = Object.keys(byDate)
    .sort((a, b) => b.localeCompare(a))
    .map((date) => ({
      title: new Date(date).toLocaleDateString('en-IN', {
        weekday: 'short', day: 'numeric', month: 'short', year: 'numeric',
      }),
      data: byDate[date].sort((a, b) => a.rank - b.rank),
    }));

  return (
    <View style={styles.container}>
      {/* Filter pills */}
      <View style={styles.filterRow}>
        {([7, 14, 30] as DayFilter[]).map((d) => (
          <TouchableOpacity
            key={d}
            style={[styles.pill, days === d && styles.pillActive]}
            onPress={() => setDays(d)}
          >
            <Text style={[styles.pillText, days === d && styles.pillTextActive]}>
              {d} Days
            </Text>
          </TouchableOpacity>
        ))}
        <Text style={styles.countText}>
          {data ? `${Object.keys(byDate).length} sessions` : ''}
        </Text>
      </View>

      {isLoading && (
        <View style={styles.centered}>
          <Text style={styles.loadingText}>Loading history…</Text>
        </View>
      )}

      {isError && (
        <View style={styles.centered}>
          <Ionicons name="alert-circle-outline" size={40} color={Colors.loss} />
          <Text style={styles.errorText}>Failed to load history</Text>
          <TouchableOpacity onPress={() => refetch()}>
            <Text style={styles.retryText}>Retry</Text>
          </TouchableOpacity>
        </View>
      )}

      {!isLoading && !isError && sections.length === 0 && (
        <View style={styles.centered}>
          <Ionicons name="time-outline" size={56} color={Colors.textMuted} />
          <Text style={styles.emptyTitle}>No history yet</Text>
          <Text style={styles.emptySub}>
            Recommendations will appear here after the daily analysis runs.
          </Text>
        </View>
      )}

      {!isLoading && sections.length > 0 && (
        <SectionList
          sections={sections}
          keyExtractor={(item) => String(item.id)}
          renderItem={({ item }) => (
            <StockCard
              rec={item}
              onPress={(r) => navigation.navigate('StockDetail', { symbol: r.symbol, rec: r })}
            />
          )}
          renderSectionHeader={({ section }) => (
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionTitle}>{section.title}</Text>
              <Text style={styles.sectionCount}>{section.data.length} picks</Text>
            </View>
          )}
          contentContainerStyle={{ paddingBottom: 80 }}
          showsVerticalScrollIndicator={false}
          refreshControl={
            <RefreshControl
              refreshing={false}
              onRefresh={onRefresh}
              tintColor={Colors.primary}
            />
          }
        />
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  filterRow: {
    flexDirection: 'row', alignItems: 'center', gap: Spacing.sm,
    paddingHorizontal: Spacing.md, paddingVertical: Spacing.sm,
    backgroundColor: Colors.surface, borderBottomWidth: 1, borderColor: Colors.border,
  },
  pill: {
    paddingHorizontal: 14, paddingVertical: 6,
    borderRadius: Radius.full, borderWidth: 1, borderColor: Colors.border,
    backgroundColor: Colors.card,
  },
  pillActive: { backgroundColor: Colors.primary + '22', borderColor: Colors.primary },
  pillText: { color: Colors.textSecondary, fontSize: 13, fontWeight: '600' },
  pillTextActive: { color: Colors.primary },
  countText: { marginLeft: 'auto', color: Colors.textMuted, fontSize: 11 },
  centered: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: Spacing.xl },
  loadingText: { color: Colors.textSecondary, fontSize: 14 },
  errorText: { color: Colors.loss, marginTop: Spacing.sm, fontSize: 14 },
  retryText: { color: Colors.primary, marginTop: Spacing.sm, fontSize: 14, fontWeight: '600' },
  sectionHeader: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingHorizontal: Spacing.md, paddingVertical: Spacing.sm,
    backgroundColor: Colors.background,
  },
  sectionTitle: { color: Colors.textPrimary, fontSize: 14, fontWeight: '700' },
  sectionCount: { color: Colors.textMuted, fontSize: 12 },
  emptyTitle: { color: Colors.textPrimary, fontSize: 18, fontWeight: '700', marginTop: Spacing.md },
  emptySub: {
    color: Colors.textSecondary, fontSize: 13,
    textAlign: 'center', marginTop: Spacing.sm, lineHeight: 20,
  },
});
