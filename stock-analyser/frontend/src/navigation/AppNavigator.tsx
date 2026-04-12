import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createStackNavigator } from '@react-navigation/stack';
import { Ionicons } from '@expo/vector-icons';

import { HomeScreen }        from '../screens/HomeScreen';
import { HistoryScreen }     from '../screens/HistoryScreen';
import { SearchScreen }      from '../screens/SearchScreen';
import { StockDetailScreen } from '../screens/StockDetailScreen';
import { Colors }            from '../theme';
import { Recommendation }    from '../types';

type RootTabParamList = {
  Home: undefined;
  History: undefined;
  Search: undefined;
};

type RootStackParamList = {
  HomeMain: undefined;
  HistoryMain: undefined;
  SearchMain: undefined;
  StockDetail: { symbol: string; rec?: Recommendation };
};

const Tab   = createBottomTabNavigator<RootTabParamList>();
const Stack = createStackNavigator<RootStackParamList>();

const screenOptions = {
  headerStyle: { backgroundColor: Colors.surface },
  headerTintColor: Colors.textPrimary,
  headerTitleStyle: { fontWeight: '700' as const, color: Colors.textPrimary },
  cardStyle: { backgroundColor: Colors.background },
};

function HomeStack() {
  return (
    <Stack.Navigator screenOptions={screenOptions}>
      <Stack.Screen
        name="HomeMain"
        component={HomeScreen}
        options={{ title: 'Today\'s Picks' }}
      />
      <Stack.Screen
        name="StockDetail"
        options={({ route }) => ({ title: route.params?.symbol ?? 'Stock Analysis' })}
      >
        {(props) => <StockDetailScreen {...props} />}
      </Stack.Screen>
    </Stack.Navigator>
  );
}

function HistoryStack() {
  return (
    <Stack.Navigator screenOptions={screenOptions}>
      <Stack.Screen name="HistoryMain" component={HistoryScreen} options={{ title: 'History' }} />
      <Stack.Screen
        name="StockDetail"
        options={({ route }) => ({ title: route.params?.symbol ?? 'Stock Analysis' })}
      >
        {(props) => <StockDetailScreen {...props} />}
      </Stack.Screen>
    </Stack.Navigator>
  );
}

function SearchStack() {
  return (
    <Stack.Navigator screenOptions={screenOptions}>
      <Stack.Screen name="SearchMain" component={SearchScreen} options={{ title: 'Analyse Any Stock' }} />
      <Stack.Screen
        name="StockDetail"
        options={({ route }) => ({ title: route.params?.symbol ?? 'Stock Analysis' })}
      >
        {(props) => <StockDetailScreen {...props} />}
      </Stack.Screen>
    </Stack.Navigator>
  );
}

export const AppNavigator = () => (
  <NavigationContainer>
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarStyle: {
          backgroundColor: Colors.surface,
          borderTopColor: Colors.border,
          height: 60,
          paddingBottom: 8,
        },
        tabBarActiveTintColor: Colors.primary,
        tabBarInactiveTintColor: Colors.textMuted,
        tabBarLabelStyle: { fontSize: 11, fontWeight: '600' },
        tabBarIcon: ({ focused, color, size }) => {
          let iconName: React.ComponentProps<typeof Ionicons>['name'] = 'home';
          if (route.name === 'Home')    iconName = focused ? 'home'          : 'home-outline';
          if (route.name === 'History') iconName = focused ? 'time'          : 'time-outline';
          if (route.name === 'Search')  iconName = focused ? 'search'        : 'search-outline';
          return <Ionicons name={iconName} size={size} color={color} />;
        },
      })}
    >
      <Tab.Screen name="Home"    component={HomeStack}    options={{ title: "Today's Picks" }} />
      <Tab.Screen name="History" component={HistoryStack} options={{ title: 'History' }} />
      <Tab.Screen name="Search"  component={SearchStack}  options={{ title: 'Search' }} />
    </Tab.Navigator>
  </NavigationContainer>
);
