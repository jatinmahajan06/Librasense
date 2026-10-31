from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import pandas as pd
import numpy as np
import os, io
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "librasense-local-demo-key"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)
DATA_FILE = os.path.join(DATA_DIR, "library_books.csv")

REQUIRED = ["book_id","title","author","category","total_copies","available_copies","borrow_count","rating","return_days"]

def seed_data():
    rows = [
      ["B001","Atomic Habits","James Clear","Self Help",8,2,142,4.8,3],
      ["B002","The Psychology of Money","Morgan Housel","Finance",6,1,118,4.7,2],
      ["B003","Clean Code","Robert C. Martin","Technology",5,0,96,4.6,5],
      ["B004","Python Crash Course","Eric Matthes","Technology",7,3,89,4.7,1],
      ["B005","Data Science from Scratch","Joel Grus","Data Science",4,1,72,4.3,4],
      ["B006","The Alchemist","Paulo Coelho","Fiction",9,5,68,4.4,2],
      ["B007","Rich Dad Poor Dad","Robert Kiyosaki","Finance",6,4,64,4.2,1],
      ["B008","Deep Work","Cal Newport","Productivity",4,0,61,4.5,6],
      ["B009","Introduction to Algorithms","Cormen et al.","Technology",3,1,55,4.6,3],
      ["B010","Ikigai","Héctor García","Self Help",7,6,42,4.1,1],
      ["B011","Machine Learning Yearning","Andrew Ng","Data Science",3,2,39,4.5,2],
      ["B012","The Great Gatsby","F. Scott Fitzgerald","Fiction",5,4,12,3.9,1],
      ["B013","Database System Concepts","Silberschatz et al.","Technology",4,3,10,4.0,2],
      ["B014","Wings of Fire","A. P. J. Abdul Kalam","Biography",6,5,9,4.8,1],
      ["B015","Thinking, Fast and Slow","Daniel Kahneman","Psychology",3,3,8,4.2,1],
      ["B016","Sapiens","Yuval Noah Harari","History",4,4,6,4.4,1],
    ]
    df=pd.DataFrame(rows,columns=REQUIRED)
    df.to_csv(DATA_FILE,index=False)

def load_df():
    if not os.path.exists(DATA_FILE): seed_data()
    df=pd.read_csv(DATA_FILE)
    for c in ["total_copies","available_copies","borrow_count","rating","return_days"]:
        df[c]=pd.to_numeric(df[c],errors="coerce").fillna(0)
    df["total_copies"]=df["total_copies"].clip(lower=0)
    df["available_copies"]=df["available_copies"].clip(lower=0)
    df["borrow_count"]=df["borrow_count"].clip(lower=0)
    df["rating"]=df["rating"].clip(0,5)
    df["return_days"]=df["return_days"].clip(lower=0)
    return df

def enrich(df):
    df=df.copy()
    denom=max(float(df["borrow_count"].max()),1)
    # Weighted demand score: borrowing popularity + scarcity + rating, scaled to 100.
    popularity=(df["borrow_count"]/denom)*55
    scarcity=np.where(df["total_copies"]>0,(1-df["available_copies"]/df["total_copies"].replace(0,1))*30,0)
    rating=(df["rating"]/5)*15
    df["demand_score"]=(popularity+scarcity+rating).round().clip(0,100)
    df["availability_pct"]=np.where(df["total_copies"]>0,100*df["available_copies"]/df["total_copies"],0).round()
    df["status"]=np.where(df["available_copies"]<=0,"Unavailable",np.where(df["available_copies"]<=1,"Low stock","Available"))
    df["recommendation"]=np.where((df["demand_score"]>=65)&(df["available_copies"]<=1),"High priority",
       np.where((df["demand_score"]>=50)&(df["available_copies"]<=2),"Consider buying","Monitor"))
    return df

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/books")
def books():
    df=enrich(load_df())
    q=request.args.get("q","").strip().lower()
    cat=request.args.get("category","")
    if q:
        mask=df[["title","author","category","book_id"]].astype(str).apply(lambda col: col.str.lower().str.contains(q,regex=False)).any(axis=1)
        df=df[mask]
    if cat and cat!="All categories": df=df[df["category"]==cat]
    return jsonify(df.fillna("").to_dict(orient="records"))

@app.route("/api/dashboard")
def dashboard():
    df=enrich(load_df())
    top=df.sort_values("borrow_count",ascending=False).head(5)
    under=df.sort_values("borrow_count").head(5)
    total_titles=int(len(df)); copies=int(df.total_copies.sum()); available=int(df.available_copies.sum())
    low=int((df.available_copies<=1).sum())
    avg_demand=round(float(df.demand_score.mean()),1) if len(df) else 0
    cats=df.groupby("category").borrow_count.sum().sort_values(ascending=False)
    insights=[]
    if len(df):
        best=df.loc[df.borrow_count.idxmax()]
        insights.append(f'"{best.title}" leads borrowing with {int(best.borrow_count)} recorded loans.')
        if low: insights.append(f"{low} title(s) have one or zero copies available; review replenishment.")
        hi=df[df.demand_score>=65]
        if len(hi): insights.append(f"{len(hi)} title(s) have high demand scores and deserve a stock review.")
        if len(df[df.borrow_count==0]): insights.append(f"{len(df[df.borrow_count==0])} title(s) have no recorded borrowing; consider promotion or collection review.")
    return jsonify({
      "total_titles":total_titles,"total_copies":copies,"available_copies":available,
      "borrowed_copies":max(copies-available,0),"low_stock":low,"avg_demand":avg_demand,
      "top_books":top[["title","borrow_count","category"]].to_dict(orient="records"),
      "underused":under[["title","borrow_count","category"]].to_dict(orient="records"),
      "categories":{"labels":cats.index.tolist(),"values":cats.values.tolist()},
      "insights":insights
    })

@app.route("/api/borrow/<book_id>",methods=["POST"])
def borrow(book_id):
    df=load_df()
    ix=df.index[df.book_id.astype(str)==book_id]
    if len(ix)==0: return jsonify({"ok":False,"message":"Book not found."}),404
    i=ix[0]
    if df.at[i,"available_copies"]<=0: return jsonify({"ok":False,"message":"No copies are currently available."}),400
    df.at[i,"available_copies"]-=1
    df.at[i,"borrow_count"]+=1
    df.to_csv(DATA_FILE,index=False)
    return jsonify({"ok":True,"message":"Demo checkout recorded. Availability has been updated."})

@app.route("/api/return/<book_id>",methods=["POST"])
def return_book(book_id):
    df=load_df()
    ix=df.index[df.book_id.astype(str)==book_id]
    if len(ix)==0: return jsonify({"ok":False,"message":"Book not found."}),404
    i=ix[0]
    df.at[i,"available_copies"]=min(df.at[i,"available_copies"]+1,df.at[i,"total_copies"])
    df.to_csv(DATA_FILE,index=False)
    return jsonify({"ok":True,"message":"Demo return recorded. Availability has been updated."})

@app.route("/upload",methods=["POST"])
def upload():
    f=request.files.get("dataset")
    if not f or not f.filename:
        flash("Choose a CSV file first.", "error"); return redirect(url_for("index"))
    try:
        incoming=pd.read_csv(f)
        incoming.columns=[str(c).strip().lower().replace(" ","_") for c in incoming.columns]
        aliases={"id":"book_id","book_title":"title","name":"title","copies":"total_copies","available":"available_copies","borrowed_count":"borrow_count","loans":"borrow_count","avg_rating":"rating","expected_return_days":"return_days"}
        incoming=incoming.rename(columns={c:aliases[c] for c in incoming.columns if c in aliases})
        missing=[c for c in REQUIRED if c not in incoming.columns]
        if missing:
            flash("CSV missing required columns: "+", ".join(missing), "error"); return redirect(url_for("index"))
        incoming=incoming[REQUIRED].copy()
        for c in ["book_id","title","author","category"]: incoming[c]=incoming[c].fillna("").astype(str)
        for c in ["total_copies","available_copies","borrow_count","rating","return_days"]:
            incoming[c]=pd.to_numeric(incoming[c],errors="coerce").fillna(0)
        if (incoming["available_copies"]>incoming["total_copies"]).any():
            flash("Some available_copies values exceed total_copies. Please correct the CSV.", "error"); return redirect(url_for("index"))
        incoming.to_csv(DATA_FILE,index=False)
        flash(f"Dataset uploaded successfully: {len(incoming)} book records loaded.", "success")
    except Exception as e:
        flash("Could not read CSV: "+str(e), "error")
    return redirect(url_for("index"))

@app.route("/download")
def download():
    return redirect(url_for("static",filename="../data/library_books.csv"))

if __name__=="__main__":
    if not os.path.exists(DATA_FILE): seed_data()
    app.run(debug=True)
