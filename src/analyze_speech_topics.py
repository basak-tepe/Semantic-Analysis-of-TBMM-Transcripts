# analyze_topics.py
import pandas as pd
from bertopic import BERTopic
import plotly.express as px

INPUT_FILE = "../data/speeches_clean.csv"
MODEL_SAVE_PATH = "../bertopic_model"
TOPIC_SUMMARY_FILE = "../data/topic_summary.csv"

def run_topic_modeling(df: pd.DataFrame):
    print("⚙️  Training BERTopic model (this may take a while)...")
    topic_model = BERTopic(language="turkish", nr_topics="auto", verbose=True)
    topics, probs = topic_model.fit_transform(df["clean_content"])
    df["topic"] = topics
    topic_model.save(MODEL_SAVE_PATH)
    print(f"✅ Model trained and saved to {MODEL_SAVE_PATH}")
    return df, topic_model

def summarize_topics(df: pd.DataFrame, topic_model: BERTopic):
    info = topic_model.get_topic_info().rename(columns={"Topic": "topic"})
    summary = df.groupby(["speech_giver", "topic"]).size().reset_index(name="count")
    summary = summary.merge(info, on="topic", how="left")
    summary.to_csv(TOPIC_SUMMARY_FILE, index=False)
    print(f"💾 Topic summary saved to {TOPIC_SUMMARY_FILE}")
    return summary

def visualize_deputy(summary: pd.DataFrame, deputy_name: str):
    deputy_df = summary[summary["speech_giver"] == deputy_name].nlargest(10, "count")
    if deputy_df.empty:
        print(f"⚠️ No data found for deputy: {deputy_name}")
        return
    fig = px.bar(deputy_df, x="Name", y="count", title=f"Top Topics for {deputy_name}", text_auto=True)
    fig.show()

if __name__ == "__main__":
    print("📂 Loading cleaned data...")
    df = pd.read_csv(INPUT_FILE)
    invalids = df[df["clean_content"].apply(lambda x: not isinstance(x, str))]
    print(f"Num of Invalid rows: {len(invalids)}")
    df = df[df["clean_content"].notna()]
    df["clean_content"] = df["clean_content"].astype(str) # Ensure all entries are strings if not this would raise an error
    df, model = run_topic_modeling(df)
    summary = summarize_topics(df, model)

    # Example visualization
    example_deputy = "Ramazan Kaşlı"
    visualize_deputy(summary, example_deputy)
