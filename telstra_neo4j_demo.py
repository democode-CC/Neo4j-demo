from neo4j import GraphDatabase
import networkx as nx
import matplotlib.pyplot as plt
from pyvis.network import Network
import json
import matplotlib.image as mpimg
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
import urllib.request
import io

class TelstraNetworkDB:
    def __init__(self, uri, username, password):
        self.driver = GraphDatabase.driver(uri, auth=(username, password))

    def close(self):
        self.driver.close()

    def create_network_topology(self):
        with self.driver.session() as session:
            # First create all nodes (existing query)
            create_nodes_query = """
            CREATE (bs1:BaseStation {id: "BS_1001", location: "Sydney", capacity: "5G", status: "Active"}),
                   (bs2:BaseStation {id: "BS_1002", location: "Melbourne", capacity: "4G", status: "Active"}),
                   (bs3:BaseStation {id: "BS_1003", location: "Brisbane", capacity: "5G", status: "Inactive"}),
                   (r1:Router {id: "R_2001", model: "Cisco 9000", bandwidth: "10Gbps"}),
                   (r2:Router {id: "R_2002", model: "Juniper MX100", bandwidth: "5Gbps"}),
                   (f1:FiberNode {id: "FN_3001", provider: "Telstra Fiber", latency: "5ms"}),
                   (f2:FiberNode {id: "FN_3002", provider: "Telstra Fiber", latency: "7ms"}),
                   (u1:UserDevice {id: "U_4001", type: "5G Mobile", owner: "Alice"}),
                   (u2:UserDevice {id: "U_4002", type: "4G Mobile", owner: "Bob"}),
                   (u3:UserDevice {id: "U_4003", type: "Home Broadband", owner: "Charlie"})
            """
            session.run(create_nodes_query)

            # Then create relationships in separate queries
            relationships_queries = [
                """
                MATCH (bs1:BaseStation {id: "BS_1001"})
                MATCH (r1:Router {id: "R_2001"})
                CREATE (bs1)-[:CONNECTED_TO {type: "Fiber", speed: "10Gbps"}]->(r1)
                """,
                """
                MATCH (bs2:BaseStation {id: "BS_1002"})
                MATCH (r2:Router {id: "R_2002"})
                CREATE (bs2)-[:CONNECTED_TO {type: "Fiber", speed: "5Gbps"}]->(r2)
                """,
                """
                MATCH (bs3:BaseStation {id: "BS_1003"})
                MATCH (r1:Router {id: "R_2001"})
                CREATE (bs3)-[:CONNECTED_TO {type: "Fiber", speed: "10Gbps"}]->(r1)
                """,
                """
                MATCH (r1:Router {id: "R_2001"})
                MATCH (f1:FiberNode {id: "FN_3001"})
                CREATE (r1)-[:CONNECTED_TO {type: "Backbone", speed: "100Gbps"}]->(f1)
                """,
                """
                MATCH (r2:Router {id: "R_2002"})
                MATCH (f2:FiberNode {id: "FN_3002"})
                CREATE (r2)-[:CONNECTED_TO {type: "Backbone", speed: "100Gbps"}]->(f2)
                """,
                """
                MATCH (f1:FiberNode {id: "FN_3001"})
                MATCH (f2:FiberNode {id: "FN_3002"})
                CREATE (f1)-[:CONNECTED_TO {type: "Backbone", speed: "100Gbps"}]->(f2)
                """,
                """
                MATCH (u1:UserDevice {id: "U_4001"})
                MATCH (bs1:BaseStation {id: "BS_1001"})
                CREATE (u1)-[:CONNECTED_TO {type: "5G", speed: "1Gbps"}]->(bs1)
                """,
                """
                MATCH (u2:UserDevice {id: "U_4002"})
                MATCH (bs2:BaseStation {id: "BS_1002"})
                CREATE (u2)-[:CONNECTED_TO {type: "4G", speed: "100Mbps"}]->(bs2)
                """,
                """
                MATCH (u3:UserDevice {id: "U_4003"})
                MATCH (bs1:BaseStation {id: "BS_1001"})
                CREATE (u3)-[:CONNECTED_TO {type: "Fiber", speed: "1Gbps"}]->(bs1)
                """
            ]

            # Execute each relationship creation query
            for query in relationships_queries:
                session.run(query)

    def get_connections(self):
        with self.driver.session() as session:
            query = """
            MATCH (n)-[r:CONNECTED_TO]->(m)
            RETURN n.id AS source, labels(n)[0] AS source_type,
                   m.id AS target, labels(m)[0] AS target_type
            """
            result = session.run(query)
            return [dict(record) for record in result]

    def get_all_nodes_and_relationships(self):
        with self.driver.session() as session:
            # Get all nodes and relationships with relationship properties
            query = """
            MATCH (n)
            OPTIONAL MATCH (n)-[r]->(m)
            RETURN n, r, m, type(r) as relType, properties(r) as relProps
            """
            result = session.run(query)
            return [(record["n"], record["r"], record["m"], 
                    record["relType"], record["relProps"]) for record in result]

    def visualize_matplotlib(self):
        """Static visualization using Matplotlib"""
        data = self.get_all_nodes_and_relationships()
        G = nx.Graph()

        # 为不同类型的节点定义标记和颜色
        node_config = {
            "BaseStation": {
                "marker": "^",  # 三角形朝上，象征信号塔
                "color": "#FF9999",
                "size": 500
            },
            "Router": {
                "marker": "s",  # 正方形，象征路由器
                "color": "#99FF99",
                "size": 400
            },
            "FiberNode": {
                "marker": "o",  # 圆形，象征节点
                "color": "#9999FF",
                "size": 400
            },
            "UserDevice": {
                "marker": "D",  # 菱形，象征用户设备
                "color": "#FFFF99",
                "size": 300
            }
        }

        # 创建节点类型映射
        node_type_map = {}
        
        # 首先添加所有节点和边
        for node, rel, target, rel_type, rel_props in data:
            if node:
                node_id = node["id"]
                node_type = list(node.labels)[0]
                G.add_node(node_id, **dict(node))
                node_type_map[node_id] = node_type
            
            if target:
                target_id = target["id"]
                target_type = list(target.labels)[0]
                G.add_node(target_id, **dict(target))
                node_type_map[target_id] = target_type
            
            if rel:
                G.add_edge(node["id"], target["id"], **rel_props)

        # 设置布局
        pos = nx.spring_layout(G)
        plt.figure(figsize=(12, 8))

        # 按节点类型分组绘制
        for node_type in set(node_type_map.values()):
            # 获取该类型的所有节点
            node_list = [node for node, ntype in node_type_map.items() if ntype == node_type]
            if node_list:
                config = node_config.get(node_type, {
                    "marker": "o",
                    "color": "#CCCCCC",
                    "size": 300
                })
                
                nx.draw_networkx_nodes(G, pos,
                                     nodelist=node_list,
                                     node_color=config["color"],
                                     node_size=config["size"],
                                     node_shape=config["marker"],
                                     alpha=0.6)

        # 绘制边和标签
        nx.draw_networkx_edges(G, pos, edge_color='gray')
        edge_labels = nx.get_edge_attributes(G, 'type')
        nx.draw_networkx_edge_labels(G, pos, edge_labels)
        
        # 绘制节点标签
        nx.draw_networkx_labels(G, pos)

        plt.title("Telstra Network Topology")
        plt.axis('off')
        plt.savefig('network_topology.png', dpi=300, bbox_inches='tight')
        plt.close()

    def visualize_interactive(self):
        """Interactive visualization using Pyvis"""
        data = self.get_all_nodes_and_relationships()
        # Enable physics and font-awesome icons
        net = Network(height="750px", width="100%", bgcolor="#ffffff", 
                     font_color="black", directed=True)
        
        # Set different colors and icons for different node types
        node_config = {
            "BaseStation": {
                "color": "#FF9999",
                "shape": "image",
                "image": "https://raw.githubusercontent.com/FortAwesome/Font-Awesome/master/svgs/solid/broadcast-tower.svg",
                "size": 30
            },
            "Router": {
                "color": "#99FF99",
                "shape": "image",
                "image": "https://raw.githubusercontent.com/FortAwesome/Font-Awesome/master/svgs/solid/router.svg",
                "size": 30
            },
            "FiberNode": {
                "color": "#9999FF",
                "shape": "image",
                "image": "https://raw.githubusercontent.com/FortAwesome/Font-Awesome/master/svgs/solid/network-wired.svg",
                "size": 30
            },
            "UserDevice": {
                "color": "#FFFF99",
                "shape": "image",
                "image": "https://raw.githubusercontent.com/FortAwesome/Font-Awesome/master/svgs/solid/mobile-alt.svg",
                "size": 30
            }
        }

        # Add nodes and edges
        for node, rel, target, rel_type, rel_props in data:
            if node:
                node_type = list(node.labels)[0]
                config = node_config.get(node_type, {
                    "color": "#CCCCCC",
                    "shape": "image",
                    "image": "https://raw.githubusercontent.com/FortAwesome/Font-Awesome/master/svgs/solid/question.svg",
                    "size": 25
                })
                
                net.add_node(node["id"],
                            label=node["id"],
                            title=json.dumps(dict(node), indent=2),
                            color=config["color"],
                            shape=config["shape"],
                            image=config["image"],
                            size=config["size"],
                            font={'size': 12},
                            borderWidth=2,
                            borderWidthSelected=4)
            
            if target:
                target_type = list(target.labels)[0]
                config = node_config.get(target_type, {
                    "color": "#CCCCCC",
                    "shape": "image",
                    "image": "https://raw.githubusercontent.com/FortAwesome/Font-Awesome/master/svgs/solid/question.svg",
                    "size": 25
                })
                
                net.add_node(target["id"],
                            label=target["id"],
                            title=json.dumps(dict(target), indent=2),
                            color=config["color"],
                            shape=config["shape"],
                            image=config["image"],
                            size=config["size"],
                            font={'size': 12},
                            borderWidth=2,
                            borderWidthSelected=4)

            if rel:
                edge_label = f"{rel_props.get('type', 'N/A')}\n{rel_props.get('speed', 'N/A')}"
                edge_title = json.dumps(rel_props, indent=2)
                
                net.add_edge(node["id"], 
                            target["id"], 
                            label=edge_label,
                            title=edge_title,
                            font={'size': 8},
                            arrows={'to': {'enabled': True, 'scaleFactor': 0.5}},
                            color={'color': '#848484', 'highlight': '#1B4F72'})

        # Update physics options to better handle images
        net.set_options("""
        var options = {
            "nodes": {
                "font": {
                    "size": 12
                },
                "scaling": {
                    "min": 20,
                    "max": 30,
                    "label": {
                        "enabled": true,
                        "min": 14,
                        "max": 30
                    }
                },
                "shapeProperties": {
                    "useBorderWithImage": true
                }
            },
            "edges": {
                "color": {
                    "color": "#848484",
                    "highlight": "#1B4F72"
                },
                "font": {
                    "size": 8,
                    "align": "middle"
                },
                "smooth": {
                    "type": "continuous",
                    "forceDirection": "none"
                }
            },
            "physics": {
                "forceAtlas2Based": {
                    "gravitationalConstant": -50,
                    "centralGravity": 0.01,
                    "springLength": 200,
                    "springConstant": 0.08
                },
                "maxVelocity": 50,
                "minVelocity": 0.1,
                "solver": "forceAtlas2Based"
            },
            "interaction": {
                "hover": true,
                "tooltipDelay": 200
            }
        }
        """)

        # Save the network
        net.save_graph("network_topology.html")

    def visualize_plotly(self):
        """Interactive visualization using Plotly"""
        import plotly.graph_objects as go
        data = self.get_all_nodes_and_relationships()
        
        # Create node lists for different types
        nodes = {}
        edges = {'source': [], 'target': [], 'properties': []}
        node_types = set()
        
        # Process nodes and relationships
        for node, rel, target, rel_type, rel_props in data:
            if node:
                node_type = list(node.labels)[0]
                node_types.add(node_type)
                if node_type not in nodes:
                    nodes[node_type] = {'ids': [], 'labels': [], 'properties': []}
                nodes[node_type]['ids'].append(node['id'])
                nodes[node_type]['labels'].append(f"{node_type}\n{node['id']}")
                nodes[node_type]['properties'].append(dict(node))
            
            if rel and target:
                edges['source'].append(node['id'])
                edges['target'].append(target['id'])
                edges['properties'].append(rel_props)

        # Create figure
        fig = go.Figure()

        # Color scheme for different node types
        colors = {
            'BaseStation': '#FF9999',
            'Router': '#99FF99',
            'FiberNode': '#9999FF',
            'UserDevice': '#FFFF99'
        }

        # Add nodes for each type
        for node_type in nodes:
            fig.add_trace(go.Scatter(
                x=[i for i in range(len(nodes[node_type]['ids']))],
                y=[0 for _ in range(len(nodes[node_type]['ids']))],
                mode='markers+text',
                name=node_type,
                marker=dict(
                    size=40,
                    color=colors.get(node_type, '#CCCCCC'),
                    line=dict(width=2)
                ),
                text=nodes[node_type]['labels'],
                hovertext=[json.dumps(prop, indent=2) for prop in nodes[node_type]['properties']],
                hoverinfo='text'
            ))

        # Update layout
        fig.update_layout(
            title='Telstra Network Topology (Plotly)',
            showlegend=True,
            hovermode='closest',
            margin=dict(b=20,l=5,r=5,t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
        )

        # Save as HTML file
        fig.write_html("network_topology_plotly.html")

    def visualize_3d(self):
        """3D visualization using Plotly"""
        import plotly.graph_objects as go
        import numpy as np
        data = self.get_all_nodes_and_relationships()
        
        # First pass: collect all nodes
        nodes = []
        node_labels = []
        node_types = []
        node_id_to_index = {}  # Dictionary to map node IDs to their indices
        
        # First collect all nodes
        for node, _, _, _, _ in data:
            if node and node['id'] not in node_id_to_index:
                node_id_to_index[node['id']] = len(nodes)
                nodes.append(node['id'])
                node_labels.append(f"{list(node.labels)[0]}\n{node['id']}")
                node_types.append(list(node.labels)[0])
        
        # Second pass: collect edges using the node_id_to_index mapping
        edges = {'source': [], 'target': [], 'properties': []}
        for node, rel, target, _, rel_props in data:
            if rel and target and target['id'] in node_id_to_index:
                source_idx = node_id_to_index[node['id']]
                target_idx = node_id_to_index[target['id']]
                edges['source'].append(source_idx)
                edges['target'].append(target_idx)
                edges['properties'].append(rel_props)

        # Generate 3D coordinates using spherical distribution
        phi = np.linspace(0, 2*np.pi, len(nodes))
        theta = np.linspace(-np.pi/2, np.pi/2, len(nodes))
        x = 2*np.cos(theta)*np.cos(phi)
        y = 2*np.cos(theta)*np.sin(phi)
        z = 2*np.sin(theta)

        # Create figure
        fig = go.Figure()

        # Add nodes
        fig.add_trace(go.Scatter3d(
            x=x, y=y, z=z,
            mode='markers+text',
            text=node_labels,
            hovertext=[f"Type: {t}<br>ID: {i}" for t, i in zip(node_types, nodes)],
            marker=dict(
                size=10,
                color=[hash(t) % 256 for t in node_types],
                colorscale='Viridis',
                line=dict(width=2, color='white')
            )
        ))

        # Add edges
        for i in range(len(edges['source'])):
            fig.add_trace(go.Scatter3d(
                x=[x[edges['source'][i]], x[edges['target'][i]]],
                y=[y[edges['source'][i]], y[edges['target'][i]]],
                z=[z[edges['source'][i]], z[edges['target'][i]]],
                mode='lines',
                line=dict(color='gray', width=2),
                hoverinfo='none'
            ))

        # Update layout
        fig.update_layout(
            title='Telstra Network Topology (3D)',
            showlegend=False,
            scene=dict(
                xaxis=dict(showticklabels=False),
                yaxis=dict(showticklabels=False),
                zaxis=dict(showticklabels=False)
            ),
            margin=dict(r=10, l=10, b=10, t=40)
        )

        # Save as HTML file
        fig.write_html("network_topology_3d.html")

def main():
    # Read Neo4j credentials from authentication file
    with open('Neo4j-Authentication.txt', 'r') as f:
        auth_lines = f.readlines()
        uri = [line.split('=')[1].strip() for line in auth_lines if 'NEO4J_URI' in line][0]
        username = [line.split('=')[1].strip() for line in auth_lines if 'NEO4J_USERNAME' in line][0]
        password = [line.split('=')[1].strip() for line in auth_lines if 'NEO4J_PASSWORD' in line][0]

    # Initialize the database connection
    db = TelstraNetworkDB(uri, username, password)

    try:
        # Create network topology
        db.create_network_topology()
        print("Network topology created successfully!")

        # Generate visualizations
        print("Generating visualizations...")
        db.visualize_matplotlib()  # Generate static image
        db.visualize_interactive()  # Generate interactive HTML
        db.visualize_plotly()      # Generate Plotly visualization
        db.visualize_3d()          # Generate 3D visualization
        print("Visualizations generated successfully!")
        print("- Static visualization saved as 'network_topology.png'")
        print("- Interactive visualization saved as 'network_topology.html'")
        print("- Plotly visualization saved as 'network_topology_plotly.html'")
        print("- 3D visualization saved as 'network_topology_3d.html'")

    finally:
        db.close()

if __name__ == "__main__":
    main()