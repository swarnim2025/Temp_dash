import os
import gdown
import pandas as pd
import numpy as np
import plotly.express as px
from dash import Dash, html, dcc, Input, Output
import pycountry

# ---------- Download CSV if not present ----------
file_id = "1m54be9Bt2KbxrUhZ4kOKm6xQn8CHbkm_"
file_name = "tmdb_movies_countries_clean.csv"
gdown_url = f"https://drive.google.com/uc?id={file_id}"

if not os.path.exists(file_name):
    gdown.download(gdown_url, file_name, quiet=False)

# ---------- Load Dataset (Already Cleaned) ----------
df = pd.read_csv(file_name)

# ---------- ISO Alpha-3 Mapping ----------
def get_iso_alpha3_enhanced(country_name):
    manual_mapping = {
        'United States': 'USA', 'United States of America': 'USA',
        'United Kingdom': 'GBR', 'UK': 'GBR',
        'Russia': 'RUS', 'Russian Federation': 'RUS',
        'South Korea': 'KOR', 'Korea, Republic of': 'KOR',
        'North Korea': 'PRK', 'Korea, Democratic People\'s Republic of': 'PRK',
        'Czech Republic': 'CZE', 'Czechia': 'CZE',
        'Iran': 'IRN', 'Iran, Islamic Republic of': 'IRN',
        'Venezuela': 'VEN', 'Venezuela, Bolivarian Republic of': 'VEN',
        'Bolivia': 'BOL', 'Bolivia, Plurinational State of': 'BOL',
        'Taiwan': 'TWN', 'Taiwan, Province of China': 'TWN',
        'Moldova': 'MDA', 'Moldova, Republic of': 'MDA',
        'Vietnam': 'VNM', 'Viet Nam': 'VNM',
        'Macedonia': 'MKD', 'North Macedonia': 'MKD',
        'The Former Yugoslav Republic of Macedonia': 'MKD'
    }
    if country_name in manual_mapping:
        return manual_mapping[country_name]
    try:
        return pycountry.countries.lookup(country_name).alpha_3
    except:
        return None

# ---------- Summary ----------
summary = df.groupby('production_countries').agg(movie_count=('title', 'count')).reset_index()
summary['iso_alpha'] = summary['production_countries'].apply(get_iso_alpha3_enhanced)
summary.dropna(subset=['iso_alpha'], inplace=True)
summary['log_movie_count'] = np.log10(summary['movie_count'] + 1)

# ---------- Dash App ----------
app = Dash(__name__)
app.title = "Global Movie Choropleth"

app.layout = html.Div([
    html.H1("🎬 Global Movie Production", style={"textAlign": "center"}),
    dcc.Graph(id='choropleth', style={'height': '700px'})
])

@app.callback(
    Output('choropleth', 'figure'),
    Input('choropleth', 'clickData')  # Trigger redraw
)
def display_map(_):
    fig = px.choropleth(
        summary,
        locations="iso_alpha",
        color="log_movie_count",
        hover_name="production_countries",
        color_continuous_scale="plasma",
        labels={'log_movie_count': 'Log₁₀(Movies + 1)'},
        title="Global Movie Production (Log Scale)"
    )
    fig.update_traces(
        hovertemplate="<b>%{hovertext}</b><br><br>" +
                      "🎬 Movies Produced: <b>%{customdata[0]:,}</b><br>" +
                      "📈 Log Scale: %{z:.2f}<extra></extra>",
        customdata=summary[['movie_count']].values
    )
    fig.update_layout(
        geo=dict(
            showframe=False,
            showcoastlines=True,
            projection_type='natural earth',
            landcolor="rgb(243,243,243)"
        ),
        margin=dict(t=60, b=20, l=10, r=10),
        coloraxis_colorbar=dict(
            title="Log(Movies + 1)",
            tickvals=[0, 1, 2, 3, 4],
            ticktext=["1", "10", "100", "1K", "10K"]
        )
    )
    return fig

if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8080)
