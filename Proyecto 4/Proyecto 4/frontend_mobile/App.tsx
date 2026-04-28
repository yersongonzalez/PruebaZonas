import React, { useState, useEffect } from 'react';
import {
  SafeAreaView,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  useColorScheme,
  View,
  FlatList,
} from 'react-native';

interface Espacio {
  id: number;
  estado: 'libre' | 'ocupado';
}

const App = () => {
  const [espacios, setEspacios] = useState<Espacio[]>([]);
  const isDarkMode = useColorScheme() === 'dark';

  const fetchEspacios = async () => {
    try {
      const response = await fetch('http://localhost:3000/api/espacios');
      const data = await response.json();
      setEspacios(data.espacios);
    } catch (error) {
      console.error('Error fetching parking data', error);
    }
  };

  useEffect(() => {
    fetchEspacios();
    const interval = setInterval(fetchEspacios, 2000);
    return () => clearInterval(interval);
  }, []);

  const renderItem = ({ item }: { item: Espacio }) => (
    <View style={[
      styles.card, 
      item.estado === 'libre' ? styles.libre : styles.ocupado
    ]}>
      <Text style={styles.idText}>Espacio {item.id}</Text>
      <Text style={styles.statusText}>{item.estado.toUpperCase()}</Text>
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle={isDarkMode ? 'light-content' : 'dark-content'} />
      <View style={styles.header}>
        <Text style={styles.title}>Parqueo en Tiempo Real</Text>
      </View>
      <FlatList
        data={espacios}
        renderItem={renderItem}
        keyExtractor={item => item.id.toString()}
        numColumns={2}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          <Text style={styles.empty}>Conectando con el servidor...</Text>
        }
      />
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  header: {
    padding: 20,
    backgroundColor: '#FFF',
    alignItems: 'center',
    borderBottomWidth: 1,
    borderBottomColor: '#DDD',
  },
  title: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
  },
  list: {
    padding: 10,
  },
  card: {
    flex: 1,
    margin: 10,
    padding: 20,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
    elevation: 3,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    height: 120,
  },
  libre: {
    backgroundColor: '#D4EDDA',
    borderWidth: 2,
    borderColor: '#28A745',
  },
  ocupado: {
    backgroundColor: '#F8D7DA',
    borderWidth: 2,
    borderColor: '#DC3545',
  },
  idText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
  },
  statusText: {
    fontSize: 14,
    marginTop: 5,
    color: '#666',
  },
  empty: {
    textAlign: 'center',
    marginTop: 50,
    color: '#999',
  }
});

export default App;
