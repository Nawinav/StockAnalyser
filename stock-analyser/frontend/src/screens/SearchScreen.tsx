import React, { useState } from 'react';
import {
  View, Text, StyleSheet, TextInput,
  TouchableOpacity, ActivityIndicator, Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useQuery } from '@tanstack/react-query';
import { getStockAnalysis } from '../services/api';
import { Colors, Spacing, Radius, Shadow } from '../theme';

interface Props { navigation: any }

export const SearchScreen: React.FC<Props> = ({ navigation }) => {
  const [query, setQuery] = useState('');
  const [searchSymbol, setSearchSymbol] = useState('');

  const { data, isLoading, isError, isFetching } = useQuery({
    queryKey: ['search', searchSymbol],
    queryFn: () => getStockAnalysis(searchSymbol),
    enabled: searchSymbol.length >= 2,
    retry: 1,
    staleTime: 5 * 60 * 1000,
  });

  const handleSearch = () => {
    const sym = query.trim().toUpperCase();
    if (!sym) return;
    setSearchSymbol(sym);
  };

  const popularStocks = [
    'RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK',
    'AXISBANK', 'SBIN', 'LT', 'WIPRO', 'TITAN',
  ];

  return (
    <View style={styles.container}>
      {/* Search bar */}
      <View style={styles.searchBar}>
        <Ionicons name="search" size={20} color={Colors.textMuted} />
        <TextInput
          style={styles.input}
          placeholder="Enter NSE symbol (e.g. RELIANCE)"
          placeholderTextColor={Colors.textMuted}
          value={query}
          onChangeText={setQuery}
          onSubmitEditing={handleSearch}
          autoCapitalize="characters"
          autoCorrect={false}
          returnKeyType="search"
        />
        {query.length > 0 && (
          <TouchableOpacity onPress={() => { setQuery(''); setSearchSymbol(''); }}>
            <Ionicons name="close-circle" size={20} color={Colors.textMuted} />
          </TouchableOpacity>
        )}
        <TouchableOpacity style={styles.searchBtn} onPress={handleSearch} disabled={isLoading}>
          <Text style={styles.searchBtnText}>Analyse</Text>
        </TouchableOpacity>
      </View>

      {/* Quick chips */}
      {!searchSymbol && (
        <>
          <Text style={styles.quickLabel}>Popular NSE Stocks</Text>
          <View style={styles.quickRow}>
            {popularStocks.map((s) => (
              <TouchableOpacity
                key={s}
                style={styles.chip}
                onPress={() => { setQuery(s); setSearchSymbol(s); }}
              >
                <Text style={styles.chipText}>{s}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </>
      )}

      {/* Loading */}
      {isFetching && (
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={Colors.primary} />
          <Text style={styles.loadingText}>Analysing {searchSymbol}…</Text>
        </View>
      )}

      {/* Error */}
      {isError && !isFetching && searchSymbol && (
        <View style={styles.centered}>
          <Ionicons name="alert-circle-outline" size={44} color={Colors.loss} />
          <Text style={styles.errorTitle}>Symbol Not Found</Text>
          <Text style={styles.errorSub}>
            '{searchSymbol}' is not available on NSE / Yahoo Finance.{'\n'}
            Try without exchange suffix (e.g. RELIANCE, not RELIANCE.NS)
          </Text>
        </View>
      )}

      {/* Result card */}
      {data && !isFetching && (
        <TouchableOpacity
          style={styles.resultCard}
          activeOpacity={0.85}
          onPress={() => navigation.navigate('StockDetail', { symbol: data.symbol, rec: data })}
        >
          <View style={styles.resultHeader}>
            <View>
              <Text style={styles.resultSymbol}>{data.symbol}</Text>
              <Text style={styles.resultName}>{data.company_name}</Text>
            </View>
            <ScoreBadge score={data.score} />
          </View>

          <View style={styles.resultPrices}>
            <PriceInfo label="Entry ₹"  value={data.entry_price?.toFixed(2) ?? '—'} />
            <PriceInfo label="SL ₹"    value={data.stop_loss?.toFixed(2) ?? '—'}  color={Colors.loss} />
            <PriceInfo label="T1 ₹"    value={data.target1?.toFixed(2) ?? '—'}    color={Colors.profit} />
            <PriceInfo label="T2 ₹"    value={data.target2?.toFixed(2) ?? '—'}    color={Colors.profit} />
          </View>

          <View style={styles.tapHint}>
            <Text style={styles.tapHintText}>Tap for full analysis</Text>
            <Ionicons name="chevron-forward" size={14} color={Colors.textMuted} />
          </View>
        </TouchableOpacity>
      )}
    </View>
  );
};

const ScoreBadge: React.FC<{ score?: number }> = ({ score }) => {
  const color =
    !score         ? Colors.neutral
    : score >= 75  ? Colors.scoreHigh
    : score >= 55  ? Colors.scoreMid
    : Colors.scoreLow;
  return (
    <View style={[sb.badge, { borderColor: color }]}>
      <Text style={[sb.num, { color }]}>{score ?? '—'}</Text>
      <Text style={[sb.lbl, { color }]}>score</Text>
    </View>
  );
};

const PriceInfo: React.FC<{ label: string; value: string; color?: string }> = ({
  label, value, color = Colors.textPrimary,
}) => (
  <View style={{ alignItems: 'center' }}>
    <Text style={{ color: Colors.textMuted, fontSize: 9, fontWeight: '700', textTransform: 'uppercase' }}>{label}</Text>
    <Text style={{ color, fontSize: 14, fontWeight: '700', marginTop: 2 }}>{value}</Text>
  </View>
);

const sb = StyleSheet.create({
  badge: {
    width: 56, height: 56, borderRadius: 28, borderWidth: 2,
    alignItems: 'center', justifyContent: 'center',
  },
  num: { fontSize: 18, fontWeight: '900' },
  lbl: { fontSize: 9, fontWeight: '700' },
});

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background, padding: Spacing.md },
  searchBar: {
    flexDirection: 'row', alignItems: 'center', gap: Spacing.sm,
    backgroundColor: Colors.card, borderRadius: Radius.md,
    paddingHorizontal: Spacing.md, paddingVertical: Spacing.sm,
    borderWidth: 1, borderColor: Colors.border,
  },
  input: { flex: 1, color: Colors.textPrimary, fontSize: 15, fontWeight: '600' },
  searchBtn: {
    backgroundColor: Colors.primary, paddingHorizontal: 14, paddingVertical: 8,
    borderRadius: Radius.full,
  },
  searchBtnText: { color: '#000', fontWeight: '800', fontSize: 13 },
  quickLabel: {
    color: Colors.textSecondary, fontSize: 12, fontWeight: '700',
    marginTop: Spacing.lg, marginBottom: Spacing.sm,
  },
  quickRow: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.sm },
  chip: {
    backgroundColor: Colors.card, borderRadius: Radius.full,
    paddingHorizontal: 14, paddingVertical: 8,
    borderWidth: 1, borderColor: Colors.border,
  },
  chipText: { color: Colors.textSecondary, fontWeight: '600', fontSize: 13 },
  centered: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: Spacing.xl },
  loadingText: { color: Colors.textSecondary, marginTop: Spacing.md },
  errorTitle: { color: Colors.loss, fontSize: 17, fontWeight: '700', marginTop: Spacing.md },
  errorSub: { color: Colors.textSecondary, fontSize: 12, textAlign: 'center', marginTop: Spacing.sm, lineHeight: 18 },
  resultCard: {
    marginTop: Spacing.lg, backgroundColor: Colors.card, borderRadius: Radius.md,
    padding: Spacing.md, borderWidth: 1, borderColor: Colors.border, ...Shadow.card,
  },
  resultHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: Spacing.md },
  resultSymbol: { color: Colors.textPrimary, fontSize: 22, fontWeight: '800' },
  resultName: { color: Colors.textSecondary, fontSize: 12, marginTop: 2 },
  resultPrices: {
    flexDirection: 'row', justifyContent: 'space-around',
    backgroundColor: Colors.surface, borderRadius: Radius.sm,
    paddingVertical: Spacing.sm,
  },
  tapHint: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'flex-end',
    marginTop: Spacing.sm, gap: 4,
  },
  tapHintText: { color: Colors.textMuted, fontSize: 11 },
});
