import React, { useState } from 'react';
import {
  View, Text, FlatList, StyleSheet, TouchableOpacity,
  ActivityIndicator, Alert, Linking, RefreshControl,
} from 'react-native';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Ionicons } from '@expo/vector-icons';
import { getWatchlist, removeFromWatchlist, getWatchlistNews } from '../services/api';
import { WatchlistItem, NewsItem } from '../types';
import { Colors, Spacing, Radius, Shadow } from '../theme';

interface Props {
  navigation: any;
}

export const WatchlistScreen: React.FC<Props> = ({ navigation }) => {
  const qc = useQueryClient();
  const [expandedNews, setExpandedNews] = useState<Record<string, NewsItem[]>>({});
  const [loadingNews, setLoadingNews] = useState<Record<string, boolean>>({});

  const { data: items = [], isLoading, refetch } = useQuery({
    queryKey: ['watchlist'],
    queryFn: () => getWatchlist(false),
    staleTime: 5 * 60 * 1000,
  });

  const removeMutation = useMutation({
    mutationFn: removeFromWatchlist,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['watchlist'] }),
    onError: () => Alert.alert('Error', 'Could not remove from watchlist.'),
  });

  const handleRemove = (symbol: string) => {
    Alert.alert(
      'Remove from Watchlist',
      `Remove ${symbol} from your watchlist?`,
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Remove', style: 'destructive', onPress: () => removeMutation.mutate(symbol) },
      ],
    );
  };

  const handleNewsToggle = async (symbol: string) => {
    if (expandedNews[symbol] !== undefined) {
      setExpandedNews((prev) => { const n = { ...prev }; delete n[symbol]; return n; });
      return;
    }
    setLoadingNews((prev) => ({ ...prev, [symbol]: true }));
    try {
      const news = await getWatchlistNews(symbol);
      setExpandedNews((prev) => ({ ...prev, [symbol]: news }));
    } catch {
      setExpandedNews((prev) => ({ ...prev, [symbol]: [] }));
    } finally {
      setLoadingNews((prev) => ({ ...prev, [symbol]: false }));
    }
  };

  const renderItem = ({ item }: { item: WatchlistItem }) => {
    const newsItems = expandedNews[item.symbol];
    const showingNews = newsItems !== undefined;
    const loadNews = loadingNews[item.symbol];

    const priceDiff = item.current_price && item.added_price
      ? ((item.current_price - item.added_price) / item.added_price) * 100
      : null;

    return (
      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <TouchableOpacity
            onPress={() => navigation.navigate('StockDetail', { symbol: item.symbol })}
            style={{ flex: 1 }}
            activeOpacity={0.8}
          >
            <Text style={styles.symbol}>{item.symbol}</Text>
            {item.company_name ? (
              <Text style={styles.companyName} numberOfLines={1}>{item.company_name}</Text>
            ) : null}
            {item.sector ? (
              <View style={styles.sectorPill}>
                <Text style={styles.sectorText}>{item.sector}</Text>
              </View>
            ) : null}
          </TouchableOpacity>

          <View style={styles.priceBlock}>
            {item.added_price ? (
              <Text style={styles.addedPrice}>Added ₹{item.added_price.toFixed(2)}</Text>
            ) : null}
            {priceDiff !== null ? (
              <Text style={[styles.priceDiff, { color: priceDiff >= 0 ? Colors.profit : Colors.loss }]}>
                {priceDiff >= 0 ? '+' : ''}{priceDiff.toFixed(2)}%
              </Text>
            ) : null}
          </View>

          <TouchableOpacity
            onPress={() => handleRemove(item.symbol)}
            hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
            style={{ marginLeft: Spacing.sm }}
          >
            <Ionicons name="trash-outline" size={18} color={Colors.loss} />
          </TouchableOpacity>
        </View>

        {item.hold_period ? (
          <View style={styles.holdChip}>
            <Ionicons name="time-outline" size={12} color={Colors.warning} />
            <Text style={styles.holdText}>Hold: {item.hold_period}</Text>
          </View>
        ) : null}

        {/* Score */}
        {item.score ? (
          <View style={styles.scoreRow}>
            <Text style={styles.scoreLabel}>Score</Text>
            <Text style={[styles.scoreValue, { color: item.score >= 75 ? Colors.scoreHigh : item.score >= 55 ? Colors.scoreMid : Colors.scoreLow }]}>
              {item.score}
            </Text>
          </View>
        ) : null}

        {/* Added date */}
        {item.added_at ? (
          <Text style={styles.addedDate}>
            Added {new Date(item.added_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
          </Text>
        ) : null}

        {/* News toggle */}
        <TouchableOpacity style={styles.newsToggle} onPress={() => handleNewsToggle(item.symbol)} activeOpacity={0.8}>
          {loadNews ? (
            <ActivityIndicator size="small" color={Colors.primary} />
          ) : (
            <Ionicons name={showingNews ? 'chevron-up' : 'newspaper-outline'} size={14} color={Colors.primary} />
          )}
          <Text style={styles.newsToggleText}>
            {loadNews ? 'Loading news…' : showingNews ? 'Hide news' : 'Show news'}
          </Text>
        </TouchableOpacity>

        {showingNews && (
          <View style={styles.newsList}>
            {newsItems.length === 0 ? (
              <Text style={styles.noNews}>No recent news available.</Text>
            ) : (
              newsItems.map((n, i) => (
                <TouchableOpacity
                  key={i}
                  style={styles.newsItem}
                  onPress={() => n.link && Linking.openURL(n.link)}
                  activeOpacity={0.75}
                >
                  <Text style={styles.newsTitle} numberOfLines={2}>{n.title}</Text>
                  <View style={styles.newsMeta}>
                    <Text style={styles.newsPublisher}>{n.publisher}</Text>
                    {n.published_at ? (
                      <Text style={styles.newsDate}>
                        {new Date(n.published_at * 1000).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}
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

  if (isLoading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={Colors.primary} />
        <Text style={styles.loadingText}>Loading watchlist…</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={items}
        keyExtractor={(item) => item.symbol}
        renderItem={renderItem}
        contentContainerStyle={styles.list}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={false}
            onRefresh={() => qc.invalidateQueries({ queryKey: ['watchlist'] })}
            tintColor={Colors.primary}
            colors={[Colors.primary]}
          />
        }
        ListHeaderComponent={
          <View style={styles.header}>
            <Text style={styles.headerTitle}>My Watchlist</Text>
            <Text style={styles.headerSub}>{items.length} stock{items.length !== 1 ? 's' : ''} tracked</Text>
          </View>
        }
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Ionicons name="bookmark-outline" size={64} color={Colors.textMuted} />
            <Text style={styles.emptyTitle}>Watchlist is empty</Text>
            <Text style={styles.emptySub}>
              Go to the Long Term tab and tap{'\n'}the bookmark icon on any stock to add it.
            </Text>
          </View>
        }
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  centered: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: Spacing.xl },
  loadingText: { color: Colors.textSecondary, marginTop: Spacing.md, fontSize: 14 },
  list: { paddingBottom: 90 },

  header: {
    paddingHorizontal: Spacing.md,
    paddingTop: Spacing.md,
    paddingBottom: Spacing.sm,
  },
  headerTitle: { color: Colors.textPrimary, fontSize: 20, fontWeight: '800' },
  headerSub: { color: Colors.textSecondary, fontSize: 12, marginTop: 2 },

  card: {
    backgroundColor: Colors.card,
    borderRadius: Radius.md,
    marginHorizontal: Spacing.md,
    marginBottom: Spacing.sm,
    padding: Spacing.md,
    ...Shadow.card,
  },
  cardHeader: { flexDirection: 'row', alignItems: 'flex-start' },
  symbol: { color: Colors.textPrimary, fontSize: 16, fontWeight: '800', letterSpacing: 0.5 },
  companyName: { color: Colors.textSecondary, fontSize: 11, marginTop: 1 },
  sectorPill: {
    marginTop: 3, backgroundColor: Colors.border, borderRadius: Radius.sm,
    paddingHorizontal: 6, paddingVertical: 1, alignSelf: 'flex-start',
  },
  sectorText: { color: Colors.textMuted, fontSize: 10 },

  priceBlock: { alignItems: 'flex-end', marginRight: Spacing.sm },
  addedPrice: { color: Colors.textSecondary, fontSize: 11 },
  priceDiff: { fontSize: 14, fontWeight: '700', marginTop: 2 },

  holdChip: {
    flexDirection: 'row', alignItems: 'center', gap: 4,
    marginTop: Spacing.sm,
    backgroundColor: Colors.warning + '18',
    borderRadius: Radius.full, paddingHorizontal: 8, paddingVertical: 3,
    alignSelf: 'flex-start',
  },
  holdText: { color: Colors.warning, fontSize: 11, fontWeight: '600' },

  scoreRow: {
    flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: Spacing.xs,
  },
  scoreLabel: { color: Colors.textMuted, fontSize: 11 },
  scoreValue: { fontSize: 13, fontWeight: '800' },

  addedDate: { color: Colors.textMuted, fontSize: 10, marginTop: Spacing.xs },

  newsToggle: {
    flexDirection: 'row', alignItems: 'center', gap: 6,
    marginTop: Spacing.sm,
    paddingTop: Spacing.sm,
    borderTopWidth: 1, borderTopColor: Colors.border,
  },
  newsToggleText: { color: Colors.primary, fontSize: 12, fontWeight: '600' },
  newsList: { marginTop: Spacing.xs },
  noNews: { color: Colors.textMuted, fontSize: 12, textAlign: 'center', paddingVertical: Spacing.sm },
  newsItem: {
    paddingVertical: Spacing.sm,
    borderBottomWidth: 1, borderBottomColor: Colors.border,
  },
  newsTitle: { color: Colors.textPrimary, fontSize: 12, lineHeight: 17 },
  newsMeta: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 3 },
  newsPublisher: { color: Colors.primary, fontSize: 10 },
  newsDate: { color: Colors.textMuted, fontSize: 10 },

  emptyContainer: {
    alignItems: 'center', justifyContent: 'center',
    padding: Spacing.xl, marginTop: Spacing.xl,
  },
  emptyTitle: {
    color: Colors.textPrimary, fontSize: 18, fontWeight: '700', marginTop: Spacing.lg,
  },
  emptySub: {
    color: Colors.textSecondary, fontSize: 13, textAlign: 'center',
    marginTop: Spacing.sm, lineHeight: 20,
  },
});
