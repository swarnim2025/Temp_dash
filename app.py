import os
import gdown
import pandas as pd
import numpy as np
import plotly.express as px
from dash import Dash, html, dcc, Input, Output, State, callback_context
import pycountry
import copy

# ---------- Download from Google Drive if not present ----------
# file_id = "1H3Tj21PLcrKgjvWYd90H3tf378woTL6C"  # your actual file ID
# file_name = "TMDB_movie_dataset_v11.csv"
# gdown_url = f"https://drive.google.com/uc?id={file_id}"
file_id = "1wdBTc8d5Rz9Mq6U_VUjPHHuTARYr9zsS"  # <-- new file ID
file_name = "tmdb_movies_countries.csv"
gdown_url = f"https://drive.google.com/uc?id={file_id}"
if not os.path.exists(file_name):
    gdown.download(gdown_url, file_name, quiet=False)

# ---------- Load and clean dataset ----------
df = pd.read_csv(file_name)
df = df[df['title'] != 'IPL 2025']
df = df[df['production_countries'].notna()]
df = df[df['production_countries'].str.strip() != '']

df['production_countries'] = df['production_countries'].str.split(',\s*')
df['genres'] = df['genres'].str.split(',\s*')
df = df.explode('production_countries').explode('genres')
df['production_countries'] = df['production_countries'].str.strip()
df['genres'] = df['genres'].str.strip()

# Country name → ISO Alpha-3 code
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

country_genre = df.groupby(['production_countries', 'genres']).size().reset_index(name='count')
summary = df.groupby('production_countries').agg(movie_count=('title', 'count')).reset_index()
summary['iso_alpha'] = summary['production_countries'].apply(get_iso_alpha3_enhanced)
summary = summary.dropna(subset=['iso_alpha'])
summary['log_movie_count'] = np.log10(summary['movie_count'] + 1)

# ---------- Dash App ----------
app = Dash(__name__)
app.title = "Movie Choropleth Popup"

app.layout = html.Div([
    html.H1("🎬 Global Movie Production", style={"textAlign": "center"}),
    dcc.Graph(id='choropleth', style={'height': '700px'}),
    html.Div([
        html.Button("✕", id='close-button', n_clicks=0, style={
            'position': 'absolute',
            'top': '6px',
            'left': '8px',
            'fontSize': '16px',
            'border': 'none',
            'background': 'transparent',
            'cursor': 'pointer',
            'zIndex': 20
        }),
        dcc.Graph(id='genre-popup', config={'displayModeBar': False}),
    ],
    id='popup-container',
    style={
        'position': 'absolute',
        'top': '120px',
        'right': '40px',
        'width': '300px',
        'backgroundColor': 'white',
        'boxShadow': '0 4px 8px rgba(0,0,0,0.2)',
        'padding': '10px',
        'borderRadius': '10px',
        'display': 'none',
        'zIndex': 10
    })
])

@app.callback(
    Output('choropleth', 'figure'),
    Input('choropleth', 'clickData')
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

@app.callback(
    Output('genre-popup', 'figure'),
    Output('popup-container', 'style'),
    Input('choropleth', 'clickData'),
    Input('close-button', 'n_clicks'),
    State('popup-container', 'style')
)
def update_genre_popup(clickData, close_clicks, current_style):
    ctx = callback_context

    if current_style is None:
        current_style = {
            'position': 'absolute',
            'top': '120px',
            'right': '40px',
            'width': '300px',
            'backgroundColor': 'white',
            'boxShadow': '0 4px 8px rgba(0,0,0,0.2)',
            'padding': '10px',
            'borderRadius': '10px',
            'display': 'none',
            'zIndex': 10
        }

    if ctx.triggered and ctx.triggered[0]['prop_id'].startswith('close-button'):
        updated_style = copy.deepcopy(current_style)
        updated_style['display'] = 'none'
        return px.bar(title=""), updated_style

    if not clickData or 'points' not in clickData or not clickData['points']:
        updated_style = copy.deepcopy(current_style)
        updated_style['display'] = 'none'
        return px.bar(title=""), updated_style

    try:
        iso = clickData['points'][0]['location']
        country = summary.loc[summary['iso_alpha'] == iso, 'production_countries'].values[0]
    except Exception:
        updated_style = copy.deepcopy(current_style)
        updated_style['display'] = 'none'
        return px.bar(title=""), updated_style

    genre_data = (
        country_genre[country_genre['production_countries'] == country]
        .groupby('genres')['count']
        .sum()
        .reset_index()
        .sort_values(by='count', ascending=False)
        .head(10)
    )

    if genre_data.empty:
        fig = px.bar(title=f"No data available for {country}")
    else:
        fig = px.bar(
            genre_data,
            x='genres',
            y='count',
            title=f"Top Genres in {country}",
            color='count',
            color_continuous_scale='Inferno'
        )

    fig.update_layout(
        xaxis_title=None,
        yaxis_title='Movies',
        margin=dict(t=50, l=30, r=10, b=70),
        paper_bgcolor='white',
        plot_bgcolor='white'
    )

    updated_style = copy.deepcopy(current_style)
    updated_style['display'] = 'block'
    return fig, updated_style

if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8080)

