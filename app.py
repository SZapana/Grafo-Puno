"""
Sistema de navegación para Puno, Perú con interfaz web profesional
"""
from flask import Flask, render_template, request, jsonify
import osmnx as ox
import networkx as nx
import folium
from folium import plugins
import heapq
import random
import time
from geopy.geocoders import Nominatim
from geopy.distance import great_circle

app = Flask(__name__)

# Lugares emblemáticos de Puno
PUNO_LANDMARKS = {
    "Plaza de Armas": (-15.8321, -70.0284),
    "Catedral de Puno": (-15.8323, -70.0280),
    "Mirador El Condor": (-15.8400, -70.0220),
    "Parque Pino": (-15.8340, -70.0320),
    "Estación de Tren": (-15.8367, -70.0253),
    "Mercado Central": (-15.8298, -70.0316),
    "Hospital Regional": (-15.8412, -70.0227),
    "UNA Puno": (-15.8389, -70.0195),
    "Puerto de Puno": (-15.8260, -70.0340),
    "Museo Naval": (-15.8280, -70.0330),
    "Mirador Kuntur Wasi": (-15.8450, -70.0180),
    "Cerro Huajsapata": (-15.8300, -70.0400)
}

class NavigationSystem:
    def __init__(self, place_name="Puno, Puno, Peru"):
        self.place_name = place_name
        self.G = None
        self.path_edges = []
        self.start_node = None
        self.end_node = None
        self.total_distance = 0
        self.path_nodes = []
        self.route_coordinates = []
        
    def load_graph(self, network_type="drive", simplify=True):
        print(f"Descargando grafo de {self.place_name}...")
        try:
            self.G = ox.graph_from_place(
                self.place_name, 
                network_type=network_type, 
                simplify=simplify
            )
            self.G = self.G.to_undirected()
            
            for u, v, key, data in self.G.edges(keys=True, data=True):
                data['weight'] = data.get('length', 1.0)
            
            print(f"Grafo cargado! Nodos: {len(self.G.nodes)}, Aristas: {len(self.G.edges)}")
            return True
            
        except Exception as e:
            print(f"Error al cargar el grafo: {e}")
            return False
    
    def get_nearest_node(self, location):
        return ox.distance.nearest_nodes(self.G, location[1], location[0])
    
    def dijkstra(self, start, end):
        # Resetear distancias previas
        for node in self.G.nodes:
            self.G.nodes[node]["distance"] = float("inf")
            self.G.nodes[node]["previous"] = None
        
        self.G.nodes[start]["distance"] = 0
        pq = [(0, start)]
        visited = set()
        
        while pq:
            current_dist, node = heapq.heappop(pq)
            
            if node in visited:
                continue
                
            visited.add(node)
            
            if node == end:
                break
            
            if current_dist > self.G.nodes[node]["distance"]:
                continue
            
            for neighbor in self.G.neighbors(node):
                if neighbor not in visited:
                    key = list(self.G[node][neighbor].keys())[0]
                    weight = self.G[node][neighbor][key]["weight"]
                    new_dist = current_dist + weight
                    
                    if new_dist < self.G.nodes[neighbor]["distance"]:
                        self.G.nodes[neighbor]["distance"] = new_dist
                        self.G.nodes[neighbor]["previous"] = node
                        heapq.heappush(pq, (new_dist, neighbor))
        
        if self.G.nodes[end]["distance"] == float("inf"):
            return False
        
        self.total_distance = self.G.nodes[end]["distance"]
        return True
    
    def reconstruct_path(self, start, end):
        self.path_nodes = []
        curr = end
        
        while curr != start:
            prev = self.G.nodes[curr]["previous"]
            if prev is None:
                break
            self.path_nodes.append(curr)
            curr = prev
        
        self.path_nodes.append(start)
        self.path_nodes.reverse()
        
        # Obtener coordenadas para la animación
        self.route_coordinates = []
        for node in self.path_nodes:
            self.route_coordinates.append(
                (self.G.nodes[node]['y'], self.G.nodes[node]['x'])
            )
        
        return self.path_nodes
    
    def calculate_route(self, start_place, end_place):
        if start_place not in PUNO_LANDMARKS or end_place not in PUNO_LANDMARKS:
            return False
        
        start_loc = PUNO_LANDMARKS[start_place]
        end_loc = PUNO_LANDMARKS[end_place]
        
        self.start_node = self.get_nearest_node((start_loc[0], start_loc[1]))
        self.end_node = self.get_nearest_node((end_loc[0], end_loc[1]))
        
        if self.dijkstra(self.start_node, self.end_node):
            self.reconstruct_path(self.start_node, self.end_node)
            return True
        
        return False
    
    def get_route_info(self):
        return {
            "distance": round(self.total_distance, 2),
            "nodes": len(self.path_nodes),
            "coordinates": self.route_coordinates,
            "start_name": self.get_node_name(self.start_node),
            "end_name": self.get_node_name(self.end_node)
        }
    
    def get_node_name(self, node_id):
        # Buscar si el nodo tiene nombre
        if 'name' in self.G.nodes[node_id]:
            return self.G.nodes[node_id]['name']
        
        # Buscar en lugares conocidos
        node_coords = (self.G.nodes[node_id]['y'], self.G.nodes[node_id]['x'])
        for name, coords in PUNO_LANDMARKS.items():
            if great_circle(node_coords, coords).meters < 50:
                return name
        
        return f"Nodo {node_id}"

# Inicializar el sistema de navegación
nav_system = NavigationSystem()
nav_system.load_graph()

@app.route('/')
def index():
    return render_template('index.html', landmarks=list(PUNO_LANDMARKS.keys()))

@app.route('/calculate_route', methods=['POST'])
def calculate_route():
    start_place = request.form.get('start')
    end_place = request.form.get('end')
    
    if not start_place or not end_place:
        return jsonify({"error": "Seleccione origen y destino"})
    
    if start_place == end_place:
        return jsonify({"error": "El origen y destino no pueden ser iguales"})
    
    if nav_system.calculate_route(start_place, end_place):
        route_info = nav_system.get_route_info()
        return jsonify({
            "success": True,
            "route_info": route_info,
            "start_coords": PUNO_LANDMARKS[start_place],
            "end_coords": PUNO_LANDMARKS[end_place]
        })
    
    return jsonify({"error": "No se pudo calcular la ruta"})

@app.route('/map')
def show_map():
    # Crear mapa centrado en Puno
    m = folium.Map(location=[-15.8321, -70.0284], zoom_start=14)
    
    # Agregar marcadores para lugares importantes
    for name, coords in PUNO_LANDMARKS.items():
        folium.Marker(
            [coords[0], coords[1]],
            popup=name,
            icon=folium.Icon(color='blue', icon='info-sign')
        ).add_to(m)
    
    # Agregar capa de tráfico
    folium.TileLayer(
        tiles='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        attr='OpenStreetMap',
        name='Mapa Base'
    ).add_to(m)
    
    folium.TileLayer(
        tiles='https://{s}.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
        attr='Google',
        name='Google Maps',
        subdomains=['mt0', 'mt1', 'mt2', 'mt3']
    ).add_to(m)
    
    folium.TileLayer(
        tiles='https://{s}.google.com/vt/lyrs=s,h&x={x}&y={y}&z={z}',
        attr='Google',
        name='Google Satellite',
        subdomains=['mt0', 'mt1', 'mt2', 'mt3']
    ).add_to(m)
    
    folium.LayerControl().add_to(m)
    
    # Agregar botón de ubicación
    plugins.LocateControl().add_to(m)
    
    # Agregar minimapa
    plugins.MiniMap(toggle_display=True).add_to(m)
    
    # Agregar medición de distancias
    plugins.MeasureControl(position='bottomleft').add_to(m)
    
    return m._repr_html_()

if __name__ == '__main__':
    app.run(debug=True)