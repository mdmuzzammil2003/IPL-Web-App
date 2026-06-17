import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import sqlite3
import os
from flask import Flask, render_template, request

app = Flask(__name__)

# Ensure the static directory exists for generated figures
os.makedirs('static', exist_ok=True)

# Create database only if it doesn't exist
if not os.path.exists('ipl_database.db'):
    df = pd.read_csv('ipl-matches.csv')
    conn = sqlite3.connect('ipl_database.db')
    df.to_sql('matches', conn, if_exists='replace', index=False)
    conn.close()
    print("Database created successfully!")

@app.route('/')
def home():
    return render_template("home.html")

@app.route("/results", methods=["POST"])
def results():
    selected_team = request.form['team']
    team_slug = selected_team.replace(' ', '_')
   
    conn = sqlite3.connect('ipl_database.db')
    cursor = conn.cursor()
    
    # 1. KPI Queries
    match_query = "SELECT COUNT(*) FROM matches WHERE Team1 = ? OR Team2 = ?"
    win_query = "SELECT COUNT(*) FROM matches WHERE WinningTeam = ?"
    toss_query = "SELECT COUNT(*) FROM matches WHERE TossWinner = ?"
    
    cursor.execute(match_query, (selected_team, selected_team))
    total_matches = cursor.get_first() if hasattr(cursor, 'get_first') else cursor.fetchone()[0]
    
    cursor.execute(win_query, (selected_team,))
    wins = cursor.fetchone()[0]
    
    cursor.execute(toss_query, (selected_team,))
    toss_wins = cursor.fetchone()[0]
    
    losses = total_matches - wins
    win_pct = round((wins / total_matches) * 100, 1) if total_matches > 0 else 0
    toss_pct = round((toss_wins / total_matches) * 100, 1) if total_matches > 0 else 0

    # 2. Chart Generation Pipeline
    # Set seaborn styling context for publication quality aesthetics
    sns.set_theme(style="whitegrid")
    
    # CHART A: Toss Decision Pie Chart
    toss_df = pd.read_sql_query("SELECT TossDecision FROM matches WHERE TossWinner = ?", conn, params=(selected_team,))
    toss_counts = toss_df['TossDecision'].value_counts()
    
    plt.figure(figsize=(5, 5))
    colors = ['#2b6cb0', '#4299e1'] if 'field' in toss_counts.index else ['#4299e1', '#2b6cb0']
    plt.pie(toss_counts, labels=[label.capitalize() for label in toss_counts.index], autopct='%1.1f%%', startangle=140, colors=colors)
    plt.title("Strategic Toss Decisions", fontsize=14, fontweight='bold', pad=15)
    toss_chart_file = f"{team_slug}_toss.png"
    plt.savefig(os.path.join('static', toss_chart_file), bbox_inches='tight', dpi=150)
    plt.close()

    # CHART B: Historical Wins Timeline (Season by Season)
    timeline_df = pd.read_sql_query("SELECT Season FROM matches WHERE WinningTeam = ?", conn, params=(selected_team,))
    timeline_counts = timeline_df['Season'].value_counts().sort_index()
    
    plt.figure(figsize=(7, 4.5))
    sns.barplot(x=timeline_counts.index, y=timeline_counts.values, palette="Blues_d")
    plt.title("Franchise Success Timeline (Wins per Season)", fontsize=14, fontweight='bold', pad=15)
    plt.xlabel("IPL Season", fontsize=11, labelpad=10)
    plt.ylabel("Total Match Wins", fontsize=11, labelpad=10)
    plt.xticks(rotation=45)
    timeline_chart_file = f"{team_slug}_timeline.png"
    plt.savefig(os.path.join('static', timeline_chart_file), bbox_inches='tight', dpi=150)
    plt.close()

    # CHART C: Franchise Top MVPs (Player of the Match Awards)
    mvp_df = pd.read_sql_query("SELECT Player_of_Match FROM matches WHERE WinningTeam = ?", conn, params=(selected_team,))
    mvp_counts = mvp_df['Player_of_Match'].value_counts().head(5)
    
    plt.figure(figsize=(7, 4.5))
    sns.barplot(x=mvp_counts.values, y=mvp_counts.index, palette="viridis", orient='h')
    plt.title("Top Franchise Match Winners (Most MVPs)", fontsize=14, fontweight='bold', pad=15)
    plt.xlabel("Total MVP Awards Received", fontsize=11, labelpad=10)
    plt.ylabel("Player Name", fontsize=11, labelpad=10)
    mvp_chart_file = f"{team_slug}_mvp.png"
    plt.savefig(os.path.join('static', mvp_chart_file), bbox_inches='tight', dpi=150)
    plt.close()

    conn.close()
    
    return render_template(
        "results.html", 
        team=selected_team, 
        matches=total_matches, 
        wins=wins, 
        losses=losses, 
        win_pct=win_pct, 
        toss=toss_wins,
        toss_pct=toss_pct,
        toss_chart=toss_chart_file,
        timeline_chart=timeline_chart_file,
        mvp_chart=mvp_chart_file
    )

if __name__ == '__main__':
    app.run(debug=True)