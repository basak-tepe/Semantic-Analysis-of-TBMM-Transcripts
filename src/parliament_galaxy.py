import pandas as pd
import numpy as np
import plotly.graph_objects as go

# === CONFIG ===
CSV_FILE = "../data/topic_summary.csv"   # 👈 Updated path for new structure

# === LOAD DATA ===
df = pd.read_csv(CSV_FILE)

# Basic sanity check
df = df.dropna(subset=["speech_giver", "topic", "count", "Count"])
df["count"] = df["count"].astype(float)
df["Count"] = df["Count"].astype(float)

# === ENGAGEMENT RATIO ===
# engagement = share of deputy's total speeches about this topic
df["engagement_ratio"] = df["count"] / df["Count"]
df["distance"] = 1 - df["engagement_ratio"]  # smaller = stronger connection

# === RANDOM 3D POSITIONS FOR TOPICS (PLANETS) ===
topics = df["topic"].unique()
topic_positions = {
    topic: np.random.uniform(-50, 50, 3) for topic in topics
}

# === COMPUTE SATELLITE (DEPUTY) POSITIONS AROUND PLANETS ===
points = []
for _, row in df.iterrows():
    topic = row["topic"]
    speaker = row["speech_giver"]
    engagement = row["engagement_ratio"]
    distance = row["distance"]

    # Topic base coordinates
    tx, ty, tz = topic_positions[topic]

    # Random offset in spherical coordinates (to orbit around the planet)
    theta, phi = np.random.uniform(0, 2*np.pi), np.random.uniform(0, np.pi)
    x = tx + distance * np.cos(theta) * np.sin(phi)
    y = ty + distance * np.sin(theta) * np.sin(phi)
    z = tz + distance * np.cos(phi)

    points.append({
        "speech_giver": speaker,
        "topic": topic,
        "x": x,
        "y": y,
        "z": z,
        "engagement": engagement
    })

points_df = pd.DataFrame(points)
points_df = points_df.astype({"speech_giver": "string", "topic": "string"})


# === BUILD GALAXY VIEW ===
fig = go.Figure()

# 🪐 Add topic planets
for topic, (tx, ty, tz) in topic_positions.items():
    planet_size = (
        df.loc[df["topic"] == topic, "count"].sum() / df["count"].sum()
    ) * 100

    fig.add_trace(go.Scatter3d(
        x=[tx], y=[ty], z=[tz],
        mode="markers+text",
        marker=dict(size=planet_size, color="gold", opacity=0.9, symbol="circle"),
        text=[topic],
        textfont=dict(size=12, color="white"),
        textposition="top center",
        name=f"🪐 {topic}"
    ))

# 🛰 Add deputies (satellites)
fig.add_trace(go.Scatter3d(
    x=points_df["x"],
    y=points_df["y"],
    z=points_df["z"],
    mode="markers",
    marker=dict(
        size=5 + 10 * points_df["engagement"],  # stronger engagement = bigger marker
        color=points_df["engagement"],
        colorscale="Viridis",
        opacity=0.85
    ),
    text=points_df["speech_giver"] + "<br>Topic: " + points_df["topic"] +
         "<br>Engagement: " + points_df["engagement"].round(2).astype(str),
    hoverinfo="text",
    name="🛰 Deputies"
))

# === STYLE ===
fig.update_layout(
    title="🌌 Parliamentary Galaxy — Topics & Deputies",
    scene=dict(
        xaxis=dict(showbackground=False, showticklabels=False, title=""),
        yaxis=dict(showbackground=False, showticklabels=False, title=""),
        zaxis=dict(showbackground=False, showticklabels=False, title=""),
        aspectmode="cube"
    ),
    paper_bgcolor="black",
    plot_bgcolor="black",
    font=dict(color="white"),
    legend=dict(font=dict(color="white"))
)

fig.show()
