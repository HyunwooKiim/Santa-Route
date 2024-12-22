from flask import Flask, render_template
import pandas as pd
from bs4 import BeautifulSoup
from geopy.distance import geodesic
import networkx as nx

app = Flask(__name__)

# 1. SVG에서 시도의 위치 추출
def extract_locations(svg_file):
    with open(svg_file, 'r', encoding='utf-8') as file:
        svg = file.read()

    soup = BeautifulSoup(svg, "html.parser")
    locations = {}

    for path in soup.find_all('path'):
        region_name = path.get('id') or path.get('title')
        if not region_name:
            continue

        d_attribute = path.get('d')
        if d_attribute:
            coords = d_attribute.split(" ")[0].replace("M", "").split(",")
            locations[region_name] = (float(coords[0]), float(coords[1]))
    
    return locations

# 2. CSV에서 인구 데이터 로드
def load_population_data(csv_file):
    return pd.read_csv(csv_file)

# 3. 최적 경로 계산
def calculate_distance(coord1, coord2):
    return geodesic(coord1, coord2).km

def tsp_solver(data):
    locations = list(zip(data['y'], data['x']))

    G = nx.Graph()
    for i, loc1 in enumerate(locations):
        for j, loc2 in enumerate(locations):
            if i != j:
                G.add_edge(i, j, weight=calculate_distance(loc1, loc2))
    
    return nx.approximation.greedy_tsp(G, source=0)

# 4. SVG 색상 변경
def update_svg_colors(svg_file, population_data):
    with open(svg_file, 'r', encoding='utf-8') as file:
        svg = file.read()

    soup = BeautifulSoup(svg, "html.parser")

    max_population = population_data['합계'].max()
    min_population = population_data['합계'].min()

    for path in soup.find_all('path'):
        region_name = path.get('id') or path.get('title')
        if region_name and region_name in population_data['시도'].values:
            pop_value = population_data[population_data['시도'] == region_name]['합계'].values[0]
            intensity = int(255 - 200 * (pop_value - min_population) / (max_population - min_population))
            color = f"rgb({intensity}, {255 - intensity}, 0)"  # Gradient color
            path['style'] = f"fill: {color};"

    return str(soup)

# 5. 메인 라우트
@app.route("/")
def index():
    svg_file = "app/static/MAP.svg"
    csv_file = "data/Population.csv"

    try:
        # 데이터 결합
        locations = extract_locations(svg_file)
        population_data = load_population_data(csv_file)
        location_df = pd.DataFrame.from_dict(locations, orient='index', columns=['x', 'y']).reset_index()
        location_df.rename(columns={'index': '시도'}, inplace=True)

        population_data['합계'] = population_data.iloc[:, 3:].sum(axis=1)
        merged_data = pd.merge(location_df, population_data, on='시도', how='inner')

        # 최적 경로 계산
        optimal_route = tsp_solver(merged_data)
        route_names = merged_data.iloc[optimal_route]['시도'].tolist()

        # SVG 색상 업데이트
        updated_svg = update_svg_colors(svg_file, merged_data)
        with open("app/static/updated_MAP.svg", "w", encoding="utf-8") as file:
            file.write(updated_svg)

        return render_template("index.html", svg_file="updated_MAP.svg", route=route_names)

    except Exception as e:
        print(f"오류 발생: {e}")

        # 오류 발생 시 원래 SVG와 더미 데이터 반환
        route_names = [
            "서울특별시", "부산광역시", "대구광역시", "인천광역시",
            "광주광역시", "대전광역시", "울산광역시", "세종특별자치시",
            "경기도", "강원도"
        ]
        return render_template("index.html", svg_file="MAP.svg", route=route_names)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005)  # 포트를 5005로 설정